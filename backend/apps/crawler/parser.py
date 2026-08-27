from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from apps.crawler.metrics import first_party

PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}


def _rels(value: str) -> set[str]:
    return {part.strip().lower() for part in (value or "").split() if part.strip()}


def schema_types_from_blocks(blocks: list[str]) -> list[str]:
    types: list[str] = []

    def walk(node) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        raw = node.get("@type")
        if isinstance(raw, list):
            types.extend(str(item) for item in raw if item)
        elif raw:
            types.append(str(raw))
        if "@graph" in node:
            walk(node["@graph"])
        for value in node.values():
            if isinstance(value, (dict, list)):
                walk(value)

    for block in blocks:
        try:
            walk(json.loads(block))
        except json.JSONDecodeError:
            continue
    return sorted(set(types))


class PageParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.headings: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
        self.links: list[str] = []
        self.external_links: list[str] = []
        self.json_ld = False
        self.json_ld_blocks: list[str] = []
        self.images_missing_alt = 0
        self.images_total = 0
        self.html_lang = ""
        self.hreflang: list[str] = []
        self.has_favicon = False
        self.has_viewport = False
        self.has_charset = False
        self.mixed_content: list[str] = []
        self.phones: list[str] = []
        self.emails: list[str] = []
        self.address_text: list[str] = []
        self.word_parts: list[str] = []
        self._current_heading = ""
        self._heading_parts: list[str] = []
        self._in_ld = False
        self._ld_parts: list[str] = []
        self._skip = 0
        self._in_address = False
        self._address_parts: list[str] = []
        self.resources: list[dict] = []
        self.hints = {"preload": 0, "preconnect": 0, "dns-prefetch": 0, "prefetch": 0}
        self.inline_css_bytes = 0
        self.inline_js_bytes = 0
        self.lazy_images = 0
        self.eager_images = 0
        self.blocking_scripts = 0
        self.async_scripts = 0
        self.defer_scripts = 0
        self.blocking_styles = 0
        self.meta_refresh = ""
        self._in_style = False
        self._in_inline_script = False
        self._style_parts: list[str] = []
        self._script_parts: list[str] = []
        self._in_head = False

    def _resource(self, kind: str, href: str, extra: dict | None = None) -> None:
        if not href or href.startswith("data:") or href.startswith("#") or href.startswith("javascript:"):
            return
        absolute = urljoin(self.base_url, href).split("#")[0]
        host = urlparse(absolute).hostname or ""
        page_host = urlparse(self.base_url).hostname or ""
        item = {
            "type": kind,
            "url": absolute[:800],
            "host": host,
            "first_party": first_party(absolute, page_host),
            "blocking": False,
        }
        if extra:
            item.update(extra)
        self.resources.append(item)
        self._mixed(href)

    def handle_starttag(self, tag, attrs):
        data = {key: value or "" for key, value in attrs}
        if tag == "head":
            self._in_head = True
        if tag in SKIP_TAGS:
            self._skip += 1
        if tag == "html" and data.get("lang"):
            self.html_lang = data["lang"]
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            charset = data.get("charset")
            if charset:
                self.has_charset = True
            http_equiv = (data.get("http-equiv") or "").lower()
            if http_equiv == "content-type" and "charset" in (data.get("content") or "").lower():
                self.has_charset = True
            if http_equiv == "refresh":
                self.meta_refresh = data.get("content") or ""
            name = (data.get("name") or data.get("property") or data.get("http-equiv") or "").lower()
            if name == "viewport":
                self.has_viewport = True
            if name and data.get("content"):
                self.meta[name] = data["content"]
        elif tag == "link":
            rels = _rels(data.get("rel", ""))
            href = data.get("href") or ""
            if "canonical" in rels:
                self.canonical = href
            if "icon" in rels or "shortcut" in rels or "apple-touch-icon" in rels:
                self.has_favicon = True
            if "alternate" in rels and data.get("hreflang"):
                self.hreflang.append(data["hreflang"])
            if "preload" in rels:
                self.hints["preload"] += 1
            if "preconnect" in rels:
                self.hints["preconnect"] += 1
            if "dns-prefetch" in rels:
                self.hints["dns-prefetch"] += 1
            if "prefetch" in rels:
                self.hints["prefetch"] += 1
            if "stylesheet" in rels:
                blocking = (data.get("media") or "all").strip() in {"", "all", "screen"}
                self._resource("css", href, {"blocking": blocking})
                if blocking:
                    self.blocking_styles += 1
            if (data.get("as") or "").lower() == "font":
                self._resource("font", href)
            if any(item in rels for item in ("preload", "preconnect", "dns-prefetch")) and href:
                self._resource("hint", href, {"rel": ",".join(sorted(rels))})
            self._mixed(href)
        elif tag in self.headings:
            self._current_heading = tag
            self._heading_parts = []
        elif tag == "a" and data.get("href"):
            href = data["href"]
            absolute = urljoin(self.base_url, href)
            self.links.append(absolute)
            if href.lower().startswith("tel:"):
                self.phones.append(href.split(":", 1)[-1].strip())
            if href.lower().startswith("mailto:"):
                self.emails.append(href.split(":", 1)[-1].split("?")[0].strip())
        elif tag == "script":
            script_type = data.get("type", "").lower()
            if "ld+json" in script_type:
                self.json_ld = True
                self._in_ld = True
                self._ld_parts = []
            src = data.get("src") or ""
            if src:
                keys = {key.lower() for key in data}
                is_async = "async" in keys
                is_defer = "defer" in keys
                blocking = self._in_head and not is_async and not is_defer
                self._resource("js", src, {"blocking": blocking, "async": is_async, "defer": is_defer})
                if is_async:
                    self.async_scripts += 1
                elif is_defer:
                    self.defer_scripts += 1
                elif blocking:
                    self.blocking_scripts += 1
            elif "ld+json" not in script_type:
                self._in_inline_script = True
                self._script_parts = []
            self._mixed(src)
        elif tag == "style":
            self._in_style = True
            self._style_parts = []
        elif tag == "img":
            self.images_total += 1
            if not data.get("alt"):
                self.images_missing_alt += 1
            loading = (data.get("loading") or "").lower()
            if loading == "lazy":
                self.lazy_images += 1
            else:
                self.eager_images += 1
            self._resource("image", data.get("src") or "", {"lazy": loading == "lazy"})
            self._mixed(data.get("src") or "")
        elif tag == "iframe":
            self._resource("iframe", data.get("src") or "")
            self._mixed(data.get("src") or "")
        elif tag in {"video", "source"}:
            src = data.get("src") or ""
            if src:
                self._resource("video" if tag == "video" else "media", src)
            self._mixed(src)
        elif tag == "address":
            self._in_address = True
            self._address_parts = []

    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        if tag in SKIP_TAGS and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag == self._current_heading:
            self.headings[tag].append("".join(self._heading_parts).strip())
            self._current_heading = ""
        if tag == "script" and self._in_ld:
            self.json_ld_blocks.append("".join(self._ld_parts).strip())
            self._in_ld = False
        if tag == "script" and self._in_inline_script:
            self.inline_js_bytes += len("".join(self._script_parts).encode("utf-8", errors="replace"))
            self._in_inline_script = False
            self._script_parts = []
        if tag == "style" and self._in_style:
            self.inline_css_bytes += len("".join(self._style_parts).encode("utf-8", errors="replace"))
            self._in_style = False
            self._style_parts = []
        if tag == "address" and self._in_address:
            text = " ".join("".join(self._address_parts).split())
            if text:
                self.address_text.append(text)
            self._in_address = False

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        if self._current_heading:
            self._heading_parts.append(data)
        if self._in_ld:
            self._ld_parts.append(data)
        if self._in_style:
            self._style_parts.append(data)
        if self._in_inline_script:
            self._script_parts.append(data)
        if self._in_address:
            self._address_parts.append(data)
        if self._skip == 0 and not self._in_ld and data.strip():
            self.word_parts.append(data)

    def _mixed(self, href: str) -> None:
        if not href or href.startswith("data:") or href.startswith("#"):
            return
        page_https = urlparse(self.base_url).scheme == "https"
        absolute = urljoin(self.base_url, href)
        if page_https and urlparse(absolute).scheme == "http":
            self.mixed_content.append(absolute.split("#")[0])

    def result(self) -> dict:
        host = urlparse(self.base_url).hostname
        internal: list[str] = []
        external: list[str] = []
        for link in self.links:
            parsed = urlparse(link)
            if parsed.scheme not in {"http", "https"}:
                continue
            clean = link.split("#")[0]
            if parsed.hostname == host:
                internal.append(clean)
            else:
                external.append(clean)
        text = " ".join(" ".join(self.word_parts).split())
        words = [part for part in re.split(r"\s+", text) if part]
        schema_types = schema_types_from_blocks(self.json_ld_blocks)
        phones = list(dict.fromkeys(self.phones + PHONE_RE.findall(text)[:8]))
        emails = list(dict.fromkeys(self.emails))
        resources = self.resources[:80]
        by_type: dict[str, int] = {}
        third_party = 0
        duplicates = 0
        seen_urls: set[str] = set()
        for item in self.resources:
            kind = str(item.get("type") or "other")
            by_type[kind] = by_type.get(kind, 0) + 1
            if not item.get("first_party"):
                third_party += 1
            url = str(item.get("url") or "")
            if url and url in seen_urls:
                duplicates += 1
            elif url:
                seen_urls.add(url)
        title = "".join(self.title_parts).strip()
        description = str(self.meta.get("description") or "")
        return {
            "title": title,
            "title_length": len(title),
            "meta": self.meta,
            "meta_description_length": len(description),
            "canonical": self.canonical,
            "h1": self.headings["h1"],
            "headings": {key: value for key, value in self.headings.items() if value},
            "internal_links": list(dict.fromkeys(internal)),
            "external_links": list(dict.fromkeys(external))[:40],
            "json_ld": self.json_ld,
            "json_ld_types": schema_types,
            "images_missing_alt": self.images_missing_alt,
            "images_total": self.images_total,
            "html_lang": self.html_lang,
            "hreflang": list(dict.fromkeys(self.hreflang)),
            "has_favicon": self.has_favicon,
            "has_viewport": self.has_viewport,
            "has_charset": self.has_charset,
            "mixed_content": list(dict.fromkeys(self.mixed_content))[:20],
            "word_count": len(words),
            "phones": phones[:12],
            "emails": emails[:12],
            "address_text": self.address_text[:4],
            "resources": resources,
            "resource_summary": {
                "total": len(self.resources),
                "by_type": by_type,
                "js": by_type.get("js", 0),
                "css": by_type.get("css", 0),
                "images": by_type.get("image", 0),
                "fonts": by_type.get("font", 0),
                "videos": by_type.get("video", 0) + by_type.get("media", 0),
                "iframes": by_type.get("iframe", 0),
                "third_party": third_party,
                "duplicates": duplicates,
                "blocking_scripts": self.blocking_scripts,
                "blocking_styles": self.blocking_styles,
                "async_scripts": self.async_scripts,
                "defer_scripts": self.defer_scripts,
                "lazy_images": self.lazy_images,
                "eager_images": self.eager_images,
                "inline_css_bytes": self.inline_css_bytes,
                "inline_js_bytes": self.inline_js_bytes,
                "hints": dict(self.hints),
            },
            "meta_refresh": self.meta_refresh,
            "robots_meta": str(self.meta.get("robots") or ""),
        }


def parse_html(url: str, html: str) -> dict:
    parser = PageParser(url)
    parser.feed(html)
    return parser.result()
