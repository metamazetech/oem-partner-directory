import re

with open('templates/rfp_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the messy addBoqRow checkboxesHtml injection
# Originally I did: content.replace("let checkboxesHtml = '';", "let checkboxesHtml = `" + search_input_html + "`;")
# Let's revert that specific part and leave it empty so it doesn't double-inject inside the JS template.

# We'll use regex to find where it starts: let checkboxesHtml = ` <div style="padding... </div> `;
# and replace it with: let checkboxesHtml = '';
pattern = r"let checkboxesHtml = `\s*<div style=\"padding: 0\.25rem.*?</div>\s*`;"
content = re.sub(pattern, "let checkboxesHtml = '';", content, flags=re.DOTALL)

with open('templates/rfp_detail.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Cleaned up addBoqRow duplicate search bar")
