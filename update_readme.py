with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Update version
content = content.replace('(v4.9)', '(v5.8)')
content = content.replace('(v5.7)', '(v5.8)')

# Add new tools to Public Work Tools Dashboard
tools_addition = """  * **🔓 Excel Password Unlocker**: Standalone utility running fully locally to crack/strip Excel workbook encryption and sheet protection using `msoffcrypto-tool` and `openpyxl`.
  * **🛠️ System Builder Engine**: Interactive parts configuration tool for designing PCs, Servers, and Networking Racks with built-in SKU lookup constraints.
  * **⏱️ Employee Timesheet Tracker**: A dedicated productivity tracking module for daily work mapping, multi-format CSV/Excel imports, and a master dashboard for administrators.
  * **📄 In-Memory PDF Converter**: Local text extractor exporting uploads directly to editable Word (`.doc`) or tabular CSV (`.csv`) formats."""

old_pdf = "  * **dY\", In-Memory PDF Converter**: Local text extractor exporting uploads directly to editable Word (`.doc`) or tabular CSV (`.csv`) formats."
content = content.replace(old_pdf, tools_addition)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)
print('README updated.')
