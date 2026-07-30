# Changelog

All notable changes to the OEM & Partner Relationship Directory Portal will be documented in this file.

## [2.0.0] - 2026-07-30

### Added
- **📰 OEM News & Industry Updates Feed**:
  - Aggregates latest product releases, launches, and offerings for all registered OEMs directly from the internet.
  - Implements a parallel RSS feed scraper utilizing a `ThreadPoolExecutor` for fast concurrent performance (under 2 seconds).
  - Implements a "Lazy-Cron" trigger: automatically checks and refreshes news articles once a calendar day when the dashboard loads.
  - Added filter dropdown on the news feed to select and query news by specific OEMs.
  - Added manual `Refresh News` trigger with CSS loading spinner overlay.
- **🖼️ PNG, JPG, & JPEG Custom Icon Support**:
  - Custom category/folder icons now support uploading standard image formats (`.png`, `.jpg`, `.jpeg`) alongside vector `.svg` files.
  - Dynamic file presence check (searching for `.`) to identify image files versus text emojis.
- **🔄 tmp/restart.txt Trigger File**:
  - Standard Passenger WSGI reload trigger file to enable zero-downtime, non-GUI automatic application restarts upon folder extraction/upload on cPanel.

### Fixed
- **📁 Category Edit Icon 404 Route**:
  - Replaced hardcoded root-relative route actions with Flask's `url_for` route builder, resolving routing issues when hosted under subdirectory subpaths (e.g. `/oemportal`).
  - Upgraded Select Category icon picker to use flexible text inputs accompanied by an interactive picker grid of 50 popular emojis, allowing arbitrary custom emojis.
- **📂 Master Backup & Restore (Internal Server Error)**:
  - Fixed backup failure caused by in-memory `BytesIO` streams on standard Apache/Passenger configurations by refactoring exports to write to physical ZIP files inside the `uploads/` folder.
  - Added a compiler check to gracefully fall back from `ZIP_DEFLATED` to `ZIP_STORED` if `zlib` is not compiled in the cPanel host's Python environment.
  - Fixed cPanel Passenger absolute path resolution errors by extracting database and upload files relative to `database.DB_PATH` and `app.config['UPLOAD_FOLDER']` rather than working directory (`.`).
- **🔍 Fetch Logo SSL Verification**:
  - Added unverified SSL context bypass to the logo downloader's `urllib` fallback connection loop, preventing failures on servers with outdated CA certificate bundles.
- **📏 Brand Logo Size Preview**:
  - Set logo display sizes inside the admin Whitelabel branding page preview card to exactly `200px x 100px` utilizing `object-fit: contain` styling.

---

*Portal is developed by [Metamaze Private Limited](https://metamaze.co.in)*  
*Email:* it@metamaze.co.in
