with open('CHANGELOG.md', 'r', encoding='utf-8') as f:
    content = f.read()

new_log = """# OEM Portal Changelog

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

""" + content[content.index("## [v5.7.0]"):]

with open('CHANGELOG.md', 'w', encoding='utf-8') as f:
    f.write(new_log)
print('CHANGELOG updated.')
