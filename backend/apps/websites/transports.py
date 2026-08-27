from __future__ import annotations

import io
from ftplib import FTP, error_perm
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx

from apps.common.exceptions import APIError
from apps.crawler.ssrf import SSRFBlocked, resolve_and_validate_host, validate_public_http_url


class SiteTransport(Protocol):
    kind: str

    def test(self) -> str: ...
    def can_write_files(self) -> bool: ...
    def read_file(self, relative_path: str) -> bytes | None: ...
    def write_file(self, relative_path: str, content: bytes) -> None: ...
    def list_names(self) -> list[str]: ...
    def update_wordpress_settings(self, *, title: str, description: str) -> bool: ...


class MemoryTransport:
    kind = "memory"

    def __init__(self, files: dict[str, bytes] | None = None):
        self.files = dict(files or {})

    def test(self) -> str:
        return "Memory transport ready."

    def can_write_files(self) -> bool:
        return True

    def read_file(self, relative_path: str) -> bytes | None:
        return self.files.get(_safe_rel(relative_path))

    def write_file(self, relative_path: str, content: bytes) -> None:
        self.files[_safe_rel(relative_path)] = content

    def list_names(self) -> list[str]:
        return sorted(self.files)

    def update_wordpress_settings(self, *, title: str, description: str) -> bool:
        self.files["_wp_title"] = title.encode()
        self.files["_wp_description"] = description.encode()
        return True


class WordPressTransport:
    kind = "wordpress"

    def __init__(self, *, base_url: str, username: str, password: str):
        self.base_url = validate_public_http_url(base_url).rstrip("/")
        self.username = username
        self.password = password

    def test(self) -> str:
        data = self._get("/wp-json/wp/v2/users/me")
        name = data.get("name") or data.get("slug") or "WordPress user"
        return f"WordPress REST accepted for {name}."

    def can_write_files(self) -> bool:
        return False

    def read_file(self, relative_path: str) -> bytes | None:
        return None

    def write_file(self, relative_path: str, content: bytes) -> None:
        raise APIError("WordPress application passwords cannot write robots.txt or HTML files. Connect FTP, SFTP, or cPanel for file fixes.", code="VALIDATION_ERROR")

    def list_names(self) -> list[str]:
        return []

    def update_wordpress_settings(self, *, title: str, description: str) -> bool:
        self._post("/wp-json/wp/v2/settings", {"title": title[:120], "description": description[:300]})
        return True

    def _get(self, path: str) -> dict:
        return self._request("GET", path)

    def _post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, body)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        validate_public_http_url(url)
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            response = client.request(method, url, json=body, auth=(self.username, self.password))
        if response.status_code in {401, 403}:
            raise APIError("WordPress rejected the application password.", code="VALIDATION_ERROR")
        if response.status_code >= 400:
            raise APIError(f"WordPress returned HTTP {response.status_code}.", code="VALIDATION_ERROR")
        try:
            data = response.json()
        except Exception as exc:  # noqa: BLE001
            raise APIError("WordPress returned a non-JSON response.", code="VALIDATION_ERROR") from exc
        return data if isinstance(data, dict) else {}


class FtpTransport:
    kind = "ftp"

    def __init__(self, *, host: str, port: int, username: str, password: str, root_path: str):
        resolve_and_validate_host(host)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.root_path = root_path.strip("/") 

    def test(self) -> str:
        with self._client() as ftp:
            ftp.cwd(self.root_path or ".")
            return f"FTP login succeeded on {self.host}."

    def can_write_files(self) -> bool:
        return True

    def read_file(self, relative_path: str) -> bytes | None:
        buffer = io.BytesIO()
        with self._client() as ftp:
            self._cwd_root(ftp)
            try:
                ftp.retrbinary(f"RETR {_safe_rel(relative_path)}", buffer.write)
            except error_perm:
                return None
        return buffer.getvalue()

    def write_file(self, relative_path: str, content: bytes) -> None:
        with self._client() as ftp:
            self._cwd_root(ftp)
            ftp.storbinary(f"STOR {_safe_rel(relative_path)}", io.BytesIO(content))

    def list_names(self) -> list[str]:
        with self._client() as ftp:
            self._cwd_root(ftp)
            return list(ftp.nlst() or [])

    def update_wordpress_settings(self, *, title: str, description: str) -> bool:
        return False

    def _cwd_root(self, ftp: FTP) -> None:
        if self.root_path:
            ftp.cwd(self.root_path)

    def _client(self) -> FTP:
        ftp = FTP()
        ftp.connect(self.host, self.port, timeout=20)
        ftp.login(self.username, self.password)
        return ftp


class SftpTransport:
    kind = "sftp"

    def __init__(self, *, host: str, port: int, username: str, password: str, root_path: str):
        resolve_and_validate_host(host)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.root_path = root_path.strip("/")

    def test(self) -> str:
        client = self._client()
        try:
            client.listdir(self._abs(""))
        finally:
            client.close()
        return f"SFTP login succeeded on {self.host}."

    def can_write_files(self) -> bool:
        return True

    def read_file(self, relative_path: str) -> bytes | None:
        client = self._client()
        try:
            with client.open(self._abs(relative_path), "rb") as handle:
                return handle.read()
        except OSError:
            return None
        finally:
            client.close()

    def write_file(self, relative_path: str, content: bytes) -> None:
        client = self._client()
        try:
            with client.open(self._abs(relative_path), "wb") as handle:
                handle.write(content)
        finally:
            client.close()

    def list_names(self) -> list[str]:
        client = self._client()
        try:
            return list(client.listdir(self._abs("")))
        finally:
            client.close()

    def update_wordpress_settings(self, *, title: str, description: str) -> bool:
        return False

    def _abs(self, relative_path: str) -> str:
        name = _safe_rel(relative_path)
        if self.root_path:
            return f"/{self.root_path}/{name}" if name else f"/{self.root_path}"
        return f"/{name}" if name else "/"

    def _client(self):
        try:
            import paramiko
        except ImportError as exc:
            raise APIError("SFTP support requires the paramiko package on the server.", code="VALIDATION_ERROR") from exc
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.host, port=self.port, username=self.username, password=self.password, timeout=20, allow_agent=False, look_for_keys=False)
        return ssh.open_sftp()


def _safe_rel(path: str) -> str:
    cleaned = (path or "").replace("\\", "/").lstrip("/")
    if not cleaned or ".." in cleaned.split("/"):
        raise APIError("Invalid remote file path.", code="VALIDATION_ERROR")
    return cleaned


def assert_wordpress_host(*, website_url: str, wp_url: str) -> str:
    site_host = (urlparse(website_url).hostname or "").lower().removeprefix("www.")
    wp_host = (urlparse(validate_public_http_url(wp_url)).hostname or "").lower().removeprefix("www.")
    if not site_host or site_host != wp_host:
        raise APIError("WordPress URL must use the same hostname as the audited website.", code="VALIDATION_ERROR")
    return validate_public_http_url(wp_url)


def build_transport(*, kind: str, config: dict, secrets: dict, website_url: str = "") -> SiteTransport:
    username = str(secrets.get("username") or config.get("username") or "")
    password = str(secrets.get("password") or "")
    if kind == "wordpress":
        if not username or not password:
            raise APIError("WordPress username and application password are required.", code="VALIDATION_ERROR")
        wp_url = assert_wordpress_host(website_url=website_url, wp_url=str(config.get("wp_url") or website_url))
        return WordPressTransport(base_url=wp_url, username=username, password=password)
    host = str(config.get("host") or "")
    if not host:
        raise APIError("FTP/SFTP host is required.", code="VALIDATION_ERROR")
    try:
        resolve_and_validate_host(host)
    except SSRFBlocked as exc:
        raise APIError(str(exc.detail), code="SSRF_BLOCKED", status_code=400) from exc
    if not username or not password:
        raise APIError("FTP/SFTP username and password are required.", code="VALIDATION_ERROR")
    root = str(config.get("root_path") or ("public_html" if kind == "cpanel" else ""))
    if kind == "sftp":
        return SftpTransport(host=host, port=int(config.get("port") or 22), username=username, password=password, root_path=root)
    return FtpTransport(host=host, port=int(config.get("port") or 21), username=username, password=password, root_path=root)
