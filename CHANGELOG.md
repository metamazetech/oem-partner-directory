# OEM Portal Changelog

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
