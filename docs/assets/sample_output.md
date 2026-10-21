## [Eval] - 2026-10-21

### Breaking Changes

- **export:** Change CSV export columns to snake_case. (007cda7, #40)
  - *Why:* Column headers are now snake_case, so existing import scripts must be updated.
- Drop support for Python 3.8. (18f9c10)
  - *Why:* Python 3.9 or newer is now required.

### Added

- **auth:** Add OAuth login with Google. (748d941, #12)
  - *Why:* Users previously had to create a password for every deployment. OAuth removes that step so that onboarding takes seconds.
- Add dark mode toggle to settings page. (03ee426)
  - *Why:* Several users asked for it because the bright UI was hard to read at night.
- Implement rate limiting for public API. (177accd)
  - *Why:* Without limits a single client could exhaust the worker pool, which caused outages last sprint.
- Introduce retry with backoff for email sending. (7b229ba)
  - *Why:* Transient SMTP errors used to drop notifications silently.
- Users can now pin projects to the sidebar. (09df129)
  - *Why:* Teams with many projects wanted quick access to the ones they use daily.

### Fixed

- **api:** Handle empty payload in /orders. (c065af9, #31)
  - *Why:* The endpoint crashed with a 500 because the JSON body was None.
- **ui:** Button text overflowed on mobile screens. (9b1643e)
  - *Why:* Long translations were clipped because the label had a fixed width.
- Fixes crash when uploading a file with unicode name. (d94d52f, #55)
  - *Why:* The upload handler used ascii encoding which caused a UnicodeEncodeError.
- Resolve race condition in session cleanup job. (9d27c46)
  - *Why:* Two workers could delete the same session because there was no lock.

### Performance

- **db:** Add index on orders.created_at. (a046857)
  - *Why:* Dashboard queries were scanning the whole table which caused 4s page loads.
- Speed up search by caching tokenised documents. (33d8783)
  - *Why:* Search was re-tokenising every document on each request. Caching reduces response time from 900ms to 120ms.
- Reduce memory usage of report generator. (46c2976)
  - *Why:* Reports with 100k rows exhausted memory because everything was loaded at once.

### Changed

- **core:** Split billing module into smaller files. (c2f6734)
  - *Why:* This makes it easier to test each calculation in isolation.
- Rename UserManager to AccountService. (df8d171)
  - *Why:* The old name was confusing since it also handles organisations.
- Clean up unused imports across the codebase. (e27a616)
- Tidy API client. (f4c1eba)
- Move config loading into its own module. (d3f5740)
  - *Why:* Keeps settings parsing separate from business logic.

### Documentation

- Describe environment variables in README. (bf3aaaa)
- Update documentation for the webhook API. (0719ad7)

### Tests

- **api:** Cover pagination edge cases. (f423015)
- Add unit tests for the invoice calculator. (3b99ec3)

### Build & CI

- **deps:** Bump requests to 2.32. (0a17cab)
- Run tests on Python 3.11 and 3.12. (443d5f6)
- Upgrade Docker base image to python:3.12-slim. (7694617)

### Maintenance

- Make login page not explode on empty password. (62e367c)
  - *Why:* It threw a TypeError so users saw a blank screen. Now shows a validation message.
- Correct totals when discount exceeds item price. (3c60e75)
  - *Why:* Negative totals were shown to customers because the discount was not clamped.
- Show upload progress bar. (2a7428a)
  - *Why:* Large uploads looked frozen so users retried and created duplicates.
- Improve error messages. (028b3a0)
