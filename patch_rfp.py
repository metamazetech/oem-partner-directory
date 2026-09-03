import re

with open('templates/rfp_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

search_input_html = '''
    <div style="padding: 0.25rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 0.5rem; position: sticky; top: 0; background: #1e293b; z-index: 1;">
        <input type="text" placeholder="Search OEM..." onkeyup="filterOems(this)" onclick="event.stopPropagation()" style="width: 100%; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: white; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">
    </div>
'''

# 1. Patch the Jinja template
# Find `<div class="checkbox-list">`
content = content.replace(
    '<div class="checkbox-list">',
    search_input_html + '\n<div class="checkbox-list">'
)

# 2. Patch the addBoqRow template
# Look for `let checkboxesHtml = '';`
content = content.replace(
    "let checkboxesHtml = '';",
    "let checkboxesHtml = `" + search_input_html + "`;"
)

# 3. Add the filterOems function to the bottom of the script
script_addition = '''
function filterOems(inputElem) {
    const filter = inputElem.value.toLowerCase();
    const list = inputElem.closest('.oem-dropdown-menu').querySelector('.checkbox-list');
    const labels = list.querySelectorAll('label');
    labels.forEach(label => {
        const text = label.textContent || label.innerText;
        if (text.toLowerCase().indexOf(filter) > -1) {
            label.style.display = 'flex';
        } else {
            label.style.display = 'none';
        }
    });
}
'''
if 'function filterOems' not in content:
    content = content.replace('</script>\n</body>', script_addition + '\n</script>\n</body>')

with open('templates/rfp_detail.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("rfp_detail.html patched for searchable OEMs")
