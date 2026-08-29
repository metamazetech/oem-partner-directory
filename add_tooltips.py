import os
import re

def add_tooltips():
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    if not os.path.exists(templates_dir):
        print(f"Directory {templates_dir} does not exist.")
        return

    emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
    
    for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
            filepath = os.path.join(templates_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Process buttons and links
            def replace_tag(match):
                tag_full = match.group(0)
                tag_name = match.group(1)
                attrs = match.group(2)
                inner_text = match.group(3)
                
                # Check if it already has a title
                if 'title=' in attrs.lower():
                    return tag_full
                
                title = ""
                # Check for emojis
                if emoji_pattern.search(inner_text) or emoji_pattern.search(attrs):
                    # Clean the inner text to use as title
                    clean_text = re.sub(r'<[^>]+>', '', inner_text).strip()
                    # Remove emojis from clean text
                    clean_text = emoji_pattern.sub('', clean_text).strip()
                    if clean_text:
                        title = clean_text
                
                # Check for onclick without title
                if 'onclick=' in attrs.lower() and not title:
                    clean_text = re.sub(r'<[^>]+>', '', inner_text).strip()
                    if clean_text:
                        title = clean_text
                        
                # Check for submit buttons
                if tag_name.lower() == 'button' and 'type="submit"' in attrs.lower() and not title:
                    clean_text = re.sub(r'<[^>]+>', '', inner_text).strip()
                    if clean_text:
                        title = clean_text
                    else:
                        title = "Submit form"
                
                if title:
                    # Insert title attribute
                    return f"<{tag_name} title=\"{title}\"{attrs}>{inner_text}</{tag_name}>"
                return tag_full

            # Match <button ...>...</button> and <a ...>...</a>
            new_content = re.sub(r'<(button|a)([^>]*)>(.*?)</\1>', replace_tag, content, flags=re.DOTALL | re.IGNORECASE)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filename}")

if __name__ == '__main__':
    add_tooltips()
