import re

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    dashboard = f.read()

with open('templates/search_results.html', 'r', encoding='utf-8') as f:
    search_res = f.read()

# Replace the whole <aside class="sidebar"> in search_results with the one from dashboard
dash_sidebar = re.search(r'(<aside class="sidebar">.*?</aside>)', dashboard, re.DOTALL)
search_sidebar = re.search(r'(<aside class="sidebar">.*?</aside>)', search_res, re.DOTALL)

if dash_sidebar and search_sidebar:
    new_search = search_res.replace(search_sidebar.group(1), dash_sidebar.group(1))
    
    # Fix the active class
    new_search = new_search.replace('<li class="nav-item active">', '<li class="nav-item">')
    
    with open('templates/search_results.html', 'w', encoding='utf-8') as f:
        f.write(new_search)
    print("search_results.html sidebar synced")
