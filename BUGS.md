# Known Issues

Local backlog for bugs that are logged but not yet fixed. Newest first.

## 2026-08-25 — `GET /api/v1/websites/` returns 500 — RESOLVED

**Update:** confirmed resolved during a later full-app QA pass (same day).
`showmigrations websites` now shows 0001-0005 all applied, and
`GET /api/v1/websites/` returns 200 with real data. Someone ran
`python manage.py migrate` locally as suggested below. Leaving the
original write-up for reference.

**Symptom:** Any authenticated request to `/api/v1/websites/` returns
`500 {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred."}}`
with no useful detail in the response or in the server logs (the custom
DRF exception handler in `backend/apps/common/exceptions.py` swallows
unrecognized exceptions into a generic `INTERNAL_ERROR` without logging
`exc_info` — worth revisiting separately, since it made this bug silent).

**Root cause (confirmed):** the local dev Postgres database is missing
migrations for the `websites` app:

```
websites
 [X] 0001_initial
 [ ] 0002_websiteaccess_auditfixrun
 [ ] 0003_keywordrankrun
 [ ] 0004_keywordrankrun_ai
 [ ] 0005_remove_auditfixrun_websites_au_tenant__fix_cr_idx_and_more
```

`WebsiteListCreateView.get_queryset()` does
`.select_related("code_access")`, which joins against the
`websites_websiteaccess` table added in `0002_websiteaccess_auditfixrun`.
Since that migration was never applied here, Postgres raises
`UndefinedTable: relation "websites_websiteaccess" does not exist`,
which the exception handler above turns into a bare 500.

**Likely fix:** run `python manage.py migrate` against the local dev
database to apply the pending `websites` migrations (0002-0005). Not
applied yet at the reporter's request — logged here for follow-up.

**Repro:**
```
POST /api/v1/auth/login/           (any tenant user)
GET  /api/v1/websites/             -> 500
```
