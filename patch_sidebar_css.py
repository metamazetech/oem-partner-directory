import re

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace left: -300px with left: -400px (to guarantee it's hidden)
content = content.replace('left: -300px;', 'left: -400px;\n        box-sizing: border-box;\n        width: 280px; /* Force consistent width */')

# Let's also add an overlay for a cleaner UI when sidebar is open
if '.sidebar-overlay' not in content:
    overlay_css = '''
.sidebar-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    z-index: 9999;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.sidebar-overlay.active {
    display: block;
    opacity: 1;
}
'''
    content += overlay_css

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("CSS updated for mobile sidebar")
