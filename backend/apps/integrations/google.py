from __future__ import annotations

import json
import re
import time
from urllib.parse import quote

import jwt

from apps.common.exceptions import APIError
from apps.integrations.probes import _client


SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SPREADSHEET_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")
SPREADSHEET_ID_RE = re.compile(r"^[a-zA-Z0-9-_]{20,}$")

LEAD_HEADERS = [
    "Company",
    "Industry",
    "Location",
    "Website",
    "Phone",
    "Email",
    "Status",
    "Lead score",
    "Opportunity",
    "Source",
    "Notes",
    "Created at",
]
RESULT_HEADERS = [
    "Website",
    "Name",
    "Overall",
    "Technical SEO",
    "On-page SEO",
    "AEO",
    "GEO",
    "Pages",
    "Issues",
    "Completed at",
]


def extract_spreadsheet_id(value: str) -> str:
    raw = (value or "").strip()
    match = SPREADSHEET_RE.search(raw)
    if match:
        return match.group(1)
    if SPREADSHEET_ID_RE.fullmatch(raw):
        return raw
    raise APIError("Paste the Google Sheet URL or the spreadsheet ID from the address bar.", code="VALIDATION_ERROR")


def parse_service_account_json(raw: str) -> tuple[str, str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise APIError("The service account file must be the full JSON Google gave you.", code="VALIDATION_ERROR") from exc
    if not isinstance(data, dict):
        raise APIError("The service account file must be the full JSON Google gave you.", code="VALIDATION_ERROR")
    email = str(data.get("client_email") or "").strip()
    key = str(data.get("private_key") or "").replace("\\n", "\n").strip()
    if not email or not key:
        raise APIError("That JSON is missing client_email or private_key. Paste the whole downloaded file.", code="VALIDATION_ERROR")
    return email, key


def google_access_token(*, client_email: str, private_key: str) -> str:
    if not client_email or not private_key:
        raise APIError("Paste the full Google service account JSON file.", code="VALIDATION_ERROR")
    now = int(time.time())
    try:
        assertion = jwt.encode(
            {
                "iss": client_email,
                "sub": client_email,
                "scope": SHEETS_SCOPE,
                "aud": TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            },
            private_key,
            algorithm="RS256",
        )
    except Exception as exc:  # noqa: BLE001
        raise APIError("The service account private key is invalid. Paste the whole JSON file Google downloaded.", code="VALIDATION_ERROR") from exc
    with _client() as client:
        response = client.post(
            TOKEN_URL,
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code in {400, 401, 403}:
        raise APIError(
            "Google rejected the service account. Share the Sheet with the service account email as Editor and enable the Google Sheets API.",
            code="INTEGRATION_AUTH",
        )
    if response.status_code >= 400:
        raise APIError(f"Google token service returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
    try:
        token = response.json().get("access_token")
    except json.JSONDecodeError as exc:
        raise APIError("Google did not return a token.", code="INTEGRATION_ERROR") from exc
    if not token:
        raise APIError("Google did not return an access token.", code="INTEGRATION_ERROR")
    return token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _range(tab: str, cells: str = "A1") -> str:
    escaped = (tab or "Sheet1").replace("'", "''")
    return quote(f"'{escaped}'!{cells}", safe="")


def probe_google_sheets(*, spreadsheet_id: str, client_email: str, private_key: str) -> None:
    sheet_id = extract_spreadsheet_id(spreadsheet_id)
    token = google_access_token(client_email=client_email, private_key=private_key)
    with _client() as client:
        response = client.get(
            f"{SHEETS_API}/{sheet_id}",
            params={"fields": "spreadsheetId,properties.title"},
            headers=_auth(token),
        )
    if response.status_code in {401, 403}:
        raise APIError(
            "Google could not open this spreadsheet. Share it with the service account email as Editor.",
            code="INTEGRATION_AUTH",
        )
    if response.status_code == 404:
        raise APIError("Spreadsheet not found. Check the ID or URL you pasted.", code="VALIDATION_ERROR")
    if response.status_code >= 400:
        raise APIError(f"Google Sheets returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")


def _ensure_tab(*, spreadsheet_id: str, title: str, headers: list[str], token: str) -> None:
    with _client() as client:
        meta = client.get(
            f"{SHEETS_API}/{spreadsheet_id}",
            params={"fields": "sheets.properties.title"},
            headers=_auth(token),
        )
        if meta.status_code >= 400:
            raise APIError(f"Google Sheets returned HTTP {meta.status_code}.", code="INTEGRATION_ERROR")
        titles = [item.get("properties", {}).get("title") for item in (meta.json().get("sheets") or [])]
        if title not in titles:
            created = client.post(
                f"{SHEETS_API}/{spreadsheet_id}:batchUpdate",
                json={"requests": [{"addSheet": {"properties": {"title": title}}}]},
                headers=_auth(token),
            )
            if created.status_code >= 400:
                raise APIError(f"Could not create the '{title}' tab (HTTP {created.status_code}).", code="INTEGRATION_ERROR")
        existing = client.get(
            f"{SHEETS_API}/{spreadsheet_id}/values/{_range(title, 'A1:Z1')}",
            headers=_auth(token),
        )
        if existing.status_code >= 400:
            raise APIError(f"Google Sheets returned HTTP {existing.status_code}.", code="INTEGRATION_ERROR")
        rows = existing.json().get("values") or []
        if not rows:
            written = client.put(
                f"{SHEETS_API}/{spreadsheet_id}/values/{_range(title, 'A1')}",
                params={"valueInputOption": "USER_ENTERED"},
                json={"values": [headers]},
                headers=_auth(token),
            )
            if written.status_code >= 400:
                raise APIError(f"Could not write headers (HTTP {written.status_code}).", code="INTEGRATION_ERROR")


def append_sheet_row(*, spreadsheet_id: str, tab: str, headers: list[str], row: list, client_email: str, private_key: str) -> None:
    sheet_id = extract_spreadsheet_id(spreadsheet_id)
    token = google_access_token(client_email=client_email, private_key=private_key)
    _ensure_tab(spreadsheet_id=sheet_id, title=tab, headers=headers, token=token)
    with _client() as client:
        response = client.post(
            f"{SHEETS_API}/{sheet_id}/values/{_range(tab, 'A1')}:append",
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            json={"values": [row]},
            headers=_auth(token),
        )
    if response.status_code >= 400:
        raise APIError(f"Google Sheets append returned HTTP {response.status_code}.", code="INTEGRATION_ERROR")
