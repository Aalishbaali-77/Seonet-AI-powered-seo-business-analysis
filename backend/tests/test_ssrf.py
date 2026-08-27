from __future__ import annotations

import pytest

from apps.crawler.ssrf import SSRFBlocked, validate_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost/admin",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "ftp://example.com/",
        "http://example.com:8080/",
    ],
)
def test_ssrf_blocked_urls(url):
    with pytest.raises(SSRFBlocked):
        validate_public_http_url(url)
