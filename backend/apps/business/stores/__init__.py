from __future__ import annotations

from apps.business.stores import ebay, etsy, shopify, woocommerce

ADAPTERS = {
    "shopify": shopify,
    "woocommerce": woocommerce,
    "etsy": etsy,
    "ebay": ebay,
}

COMMERCE_PROVIDERS = set(ADAPTERS)


def probe_store(provider: str, *, public: dict, secret: dict) -> None:
    adapter = ADAPTERS[provider]
    if provider == "shopify":
        adapter.probe(shop_domain=public.get("shop_domain", ""), access_token=secret.get("access_token", ""))
    elif provider == "woocommerce":
        adapter.probe(base_url=public.get("base_url", ""), consumer_key=secret.get("consumer_key", ""), consumer_secret=secret.get("consumer_secret", ""))
    elif provider == "etsy":
        adapter.probe(shop_id=public.get("shop_id", ""), api_key=secret.get("api_key", ""), access_token=secret.get("access_token", ""))
    else:
        adapter.probe(access_token=secret.get("access_token", ""))


def fetch_store(provider: str, *, public: dict, secret: dict) -> dict:
    adapter = ADAPTERS[provider]
    if provider == "shopify":
        return adapter.fetch(shop_domain=public.get("shop_domain", ""), access_token=secret.get("access_token", ""))
    if provider == "woocommerce":
        return adapter.fetch(base_url=public.get("base_url", ""), consumer_key=secret.get("consumer_key", ""), consumer_secret=secret.get("consumer_secret", ""))
    if provider == "etsy":
        return adapter.fetch(shop_id=public.get("shop_id", ""), api_key=secret.get("api_key", ""), access_token=secret.get("access_token", ""))
    return adapter.fetch(access_token=secret.get("access_token", ""))
