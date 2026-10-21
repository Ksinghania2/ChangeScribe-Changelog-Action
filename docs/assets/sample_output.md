## [Eval] - 2026-10-21

### Breaking Changes

- **export:** Change CSV export columns to snake_case. (cb46dba, #40)
  - *Why:* Column headers are now snake_case, so existing import scripts must be updated.
- Drop support for Python 3.8. (9f3453a)
  - *Why:* Python 3.9 or newer is now required.

### Added

- **auth:** Add OAuth login with Google. (ada8318, #12)
  - *Why:* Users previously had to create a password for every deployment. OAuth removes that step so that onboarding takes seconds.
- Add dark mode toggle to settings page. (8ac63fe)
  - *Why:* Several users asked for it because the bright UI was hard to read at night.
- Implement rate limiting for public API. (3d8d849)
  - *Why:* Without limits a single client could exhaust the worker pool, which caused outages last sprint.
- Introduce retry with backoff for email sending. (cdd66c6)
  - *Why:* Transient SMTP errors used to drop notifications silently.
- Users can now pin projects to the sidebar. (3eb935f)
  - *Why:* Teams with many projects wanted quick access to the ones they use daily.

### Fixed

- **api:** Handle empty payload in /orders. (3312208, #31)
  - *Why:* The endpoint crashed with a 500 because the JSON body was None.
- **ui:** Button text overflowed on mobile screens. (4b9e4ba)
  - *Why:* Long translations were clipped because the label had a fixed width.
- Fixes crash when uploading a file with unicode name. (2dc7409, #55)
  - *Why:* The upload handler used ascii encoding which caused a UnicodeEncodeError.
- Resolve race condition in session cleanup job. (0804935)
  - *Why:* Two workers could delete the same session because there was no lock.

### Performance

- **db:** Add index on orders.created_at. (4149963)
  - *Why:* Dashboard queries were scanning the whole table which caused 4s page loads.
- Speed up search by caching tokenised documents. (066715e)
  - *Why:* Search was re-tokenising every document on each request. Caching reduces response time from 900ms to 120ms.
- Reduce memory usage of report generator. (712cd60)
  - *Why:* Reports with 100k rows exhausted memory because everything was loaded at once.

### Changed

- **core:** Split billing module into smaller files. (32b1905)
  - *Why:* This makes it easier to test each calculation in isolation.
- Rename UserManager to AccountService. (54d1dc6)
  - *Why:* The old name was confusing since it also handles organisations.
- Clean up unused imports across the codebase. (08308fa)
- Tidy API client. (94276a2)
- Move config loading into its own module. (8ea90b5)
  - *Why:* Keeps settings parsing separate from business logic.

### Documentation

- Describe environment variables in README. (f641277)
- Update documentation for the webhook API. (50c9da4)

### Tests

- **api:** Cover pagination edge cases. (513ed16)
- Add unit tests for the invoice calculator. (8579002)

### Build & CI

- **deps:** Bump requests to 2.32. (c5ab336)
- Run tests on Python 3.11 and 3.12. (de66036)
- Upgrade Docker base image to python:3.12-slim. (61b4806)

### Maintenance

- Make login page not explode on empty password. (4ec0c2f)
  - *Why:* It threw a TypeError so users saw a blank screen. Now shows a validation message.
- Correct totals when discount exceeds item price. (a685f17)
  - *Why:* Negative totals were shown to customers because the discount was not clamped.
- Show upload progress bar. (0313cff)
  - *Why:* Large uploads looked frozen so users retried and created duplicates.
- Improve error messages. (0cc9ae1)
