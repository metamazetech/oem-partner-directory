# OEM Portal Changelog

## [v6.6.0] - 2026-10-28
### Added
- **Bank of OEMs Universal Search Engine**:
  - Deep multi-field universal search matching across `company_name`, `group_name`, `fetched_products`, `fetched_services`, `custom_products`, `custom_services`, `portfolio_summary`, `contact_persons`, and `address`.
  - **Enterprise Pre-Sales Synonym Expansion**: Automatically maps shorthand and related IT concepts (e.g. `cctv` $\rightarrow$ Camera, Surveillance, VMS, NVR; `storage` $\rightarrow$ SAN, NAS, Backup, All-Flash; `firewall` $\rightarrow$ NGFW, UTM, Cyber Security; `edr` $\rightarrow$ Endpoint, Antivirus, XDR; `switch` $\rightarrow$ Switching, Router, PoE, Catalyst; `ups` $\rightarrow$ Power, Inverter, Battery; `server` $\rightarrow$ Compute, Blade, HCI).
  - **Redesigned Bank of OEMs Directory Interface (`search_results.html`)**:
    - Dedicated top search bar with 1-click quick topic pills (`🔥 Firewall`, `💾 Storage`, `🔀 Switch`, `📹 CCTV`, `🛡️ EDR`, `💿 Backup`, `⚡ UPS`, `🖥️ Compute`, `🛠️ SLA`).
    - Filter pills for instant client-side switching between `All`, `OEMs Only`, and `Distributors`.
    - Rich OEM Bank cards with company logos, category badges, website links, and glowing `🎯 Matched Products:` and `🎯 Matched Services:` chips.
    - Product and service tag clouds displaying full hardware platform and engineering SLA offerings.
- **Solutions Portfolio 10–15 Line Product & Service Catalog Overview**:
  - Pre-sales actionable catalog overview detailing core hardware appliances, platform series, software licensing packages, hypervisor/cloud interoperability, engineering services, multi-tier SLAs (24/7/365, 4-hour on-site replacement), and RFP commercial compliance.
  - Dedicated `#portfolio-summary-card` on `contact_detail.html` with inline read-only view, instant AJAX editor (`/contact/<id>/portfolio-summary`), and audit trail logging.
  - Integration into partner onboarding, profile editing modal, and live website scraping.
- **Automated Master Offerings Refresh**:
  - Admin Panel "Fetch Offerings for All Partners" concurrently crawls partner domains and open internet sources to refresh products, services, and re-generate the tailored 10–15 line catalog summary for all existing partners.
- **Zero-Downtime Database Auto-Migration**:
  - `database.py` boot sequence automatically verifies and adds the `portfolio_summary` column and auto-populates any unpopulated partner records without downtime.

## [v6.5.0] - 2026-10-15
### Added
- **Complete Mobile View Rebuild (FSM Design System)**:
  - Rebuilt the entire mobile UI from scratch using the Field Service Management (FSM) theme architecture with modern design tokens (`#102f32` field teal, `#c7e36f` lime accents, `#ec7654` signal alerts, and `#0e1b1d` dark glass panels).
  - Unified sticky `.mobile-top-bar` with high-contrast Sanddy branding, title, live status pulsing indicator, and quick-action buttons.
  - Native-style `#sidebar` slide drawer with smooth `#drawer-overlay` backdrop blur, preventing side panel occlusion and content clipping.
  - Unified `.mobile-bottom-dock` 5-tab navigation dock with elevated center 1-tap card scanner bubble (Home, News, Scan, Timesheets, Menu).
  - Mobile bottom-sheet modals with tactile grab handles (`.sheet-drag-handle`) and full screen-height bounds.
- **Timesheet Productivity & Click-Style Time Chips**:
  - Click-style quick-fill chips for Start and End times (`09:00`, `10:00`, `11:00`, `14:00`, `16:00`, `+15m`, `+30m`, `+1h`, `+2h`, `Now`) for instant 1-tap entry without manual keyboard typing.
  - Multi-criteria ordering for Timesheet logs (A-Z by Project title, Task name, Date descending/ascending, and Time).
- **Responsive OEM & Distributor Directory**:
  - Full-width symmetrical card layout on both mobile and desktop with square-bracketed badges (`[OEM]`, `[Distributor]`).
  - 1-tap quick action shortcuts on cards (WhatsApp direct message, telephone call, and email client).

### Fixed
- **Fingerprint Registration TypeError**: Fixed `get_portal_settings()` argument mismatch in `/biometric/register/options` by supporting optional `conn=None` across `database.py` and `app.py`. Added robust WebAuthn domain heuristics and user verification fallbacks for Android smartphone fingerprint hardware.
- **Timesheet Edit 404 Route Error**: Unified the edit endpoint across `/timesheets/edit`, `/timesheets/edit/<entry_id>`, and `/timesheet/edit/<entry_id>` supporting both URL params and form-encoded IDs.
- **Attendance Geofence Radius Rejection**: Corrected the client-side office perimeter calculation to honor the dynamic office radius configured in portal settings (500m), eliminating false "outside office zone" errors.
- **Eliminated Duplicate Bottom Navs & Sticky Headers**: Stripped conflicting legacy bottom bars, duplicate hamburger icons, and sticky pseudo-elements across all templates.

## [v6.4.0] - 2026-10-13
### Added
- **1-Click Instant Camera Visiting Card Scanner**: Directly triggers the mobile rear camera (`capture="environment"`) to snap visiting cards without manual field requirements or navigating gallery pickers. Auto-extracts Company, Contact Person, Designation, Phone, Email, Website, and Address.
- **Client-Side Canvas Pre-Compression**: Scales large smartphone camera photos (>10MB) down to an optimal <400KB JPEG on an in-memory HTML5 canvas prior to uploading, eliminating cPanel upload size rejections and WSGI timeouts.
- **Mobile Camera EXIF Orientation Auto-Correction**: Transposes rotated smartphone photos before OCR processing to maintain high OCR character recognition rates.
- **Unified `/parse-card-text` API & Resilient OCR Fallback**: Enables both server-side Tesseract and in-browser `Tesseract.js` to utilize the same 100%-accurate regex extraction heuristics.
- **Contact Details "Share All"**: Native Web Share API integration on mobile devices with fallbacks to WhatsApp and formatted clipboard copy.
- **Floating Mobile Navigation Scan Action**: Added a prominent floating camera shutter bubble directly in the mobile bottom navigation bar for instantaneous thumb-reach scanning.
- **Standardized Bracketed Dropdowns**: Partner type selectors formatted with square brackets (`[All Types]`, `[OEM]`, `[Distributor]`) across the dashboard directory and modals.

### Fixed
- **Symmetrical Stats Grid & Duplicate Text**: Replaced third-party GridStack with a pure, symmetrical CSS Grid layout (4 equal desktop columns, 2x2 tablet/mobile grid) with colored glowing top borders, eliminating layout shifts and duplicate text.
- **Mobile Header Action Overflow**: Fixed rigid non-wrapping flex layout on mobile headers by implementing `.header-action-buttons` with responsive wrapping so the Scan Card and Add Partner buttons remain visible on small screens.
- **Content-Security-Policy (CSP)**: Permitted CDN scripts (`cdn.jsdelivr.net`, `unpkg.com`), `blob:` web workers, and Tesseract traineddata connections.
- **Regex Parsing Bugs**: Fixed URL truncation bug, supported multiple phone numbers on a single line, preserved parentheses and `&` characters in corporate designations, and stopped phone lines from polluting address fields.

## [v5.8.0] - 2026-10-01
### Added
- **UI/UX Refinements**: Decluttered the global navigation by moving "Excel Utility" and "System Builder Engine" exclusively into the standalone "Work Tools" module dashboard.
- **Database Auto-Migration Hook**: Integrated a zero-touch boot-time sequence check to automatically deploy DB schema adjustments and populate Change Logs for manually-extracted `.zip` deployments on restrictive cPanel environments.

### Fixed
- **Mobile Responsive Tables**: Repaired overflow breakage on small viewports (<600px). Dense DataTables and GridStack layout items now cleanly block-stack vertically to prevent infinite horizontal scrolling on smartphones.
- **Dashboard Stat Alignment**: Corrected the Flexbox CSS boundaries of the top-level overview cards (Total Partners, OEMs, Distributors, Interactions) to enforce absolute center-to-right visual alignment.
- **Background Thread DB Freezes (Massive Performance Boost)**: Reprogrammed the master Portfolio Web Scraper. Replaced locking transactions that held the SQLite connection pool hostage during 10s HTTP operations with strictly-scoped read-fetch-write cycles. The portal is incredibly fast again.
- **OEM Brand Logo Accuracy**: Resolved a silent bug where Google's `s2/favicons` API incorrectly fed default 726-byte "Globe" image placeholders as real logos. Bypassed this by establishing DuckDuckGo's exact-match `.ico` API as the primary authoritative fallback.
- **Missing Sidebar Links**: Fixed a critical Context Processor templating omission that prevented the `enabled_work_tools` variable from firing, which falsely hid the Work Tools links across the entire portal.

## [v5.7.0] - 2026-10-01
### Added
- **Timesheet & Productivity Tracker**: Dedicated tracker for employee tasks, productivity metrics, and daily workflows. Includes native CSV/Excel export functionality and a dedicated master Admin dashboard for global monitoring.
- **System Builder Engine**: Enterprise-grade interactive parts configuration tool (servers, networking, storage, PC components) allowing users to construct configurations on the fly via a rich drag-and-drop/additive UI.
- **Excel Password & Protection Remover Utility**: High-performance local utility for securely stripping Excel Worksheet/Workbook protection limits and cracking file-level encryption using background multi-threading to prevent Nginx timeouts.

### Fixed
- **CSV Data Import Failure**: Fixed a critical bug where importing exported data failed due to strict headers. The import engine now features a highly resilient dual-format parser that dynamically recognizes and ingests both the legacy (9-column) format and the modern JSON-packed multi-contact (6-column) formats.
- **Mobile Navigation Menu Dropoff**: completely revamped the entire mobile UI to simulate a native app-like experience (replacing the standard hamburger header with an iOS-style fixed bottom navigation tab bar with responsive slide-up overlay drawers).
- **cPanel WAF & Reverse Proxy Import Tarpitting**: Fully removed the javascript `XMLHttpRequest` (AJAX) progress mechanic from the `import_csv` function to resolve silent 500 error hangs and endless loading loops caused by strict cPanel ModSecurity blocking background database payloads. Replaced with standard robust HTML native form uploads.
- **Background File Handling Lockups**: Implemented strictly scoped Context Managers (`with open(...)`) for `openpyxl` & `msoffcrypto` logic, fixing silent `.xlsx` OS-level file descriptor locks that caused host server temp directories to bloat endlessly.
