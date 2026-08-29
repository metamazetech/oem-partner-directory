with open('static/css/style.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Add styles for the sidebar-collapse-btn at the end
content += """
/* Sidebar collapse button */
.sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    gap: 0.5rem;
}

#sidebar-collapse-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

@media (max-width: 768px) {
    #sidebar-collapse-btn {
        display: none;
    }
}
"""

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated style.css')
