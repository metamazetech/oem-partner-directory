with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'search' in line.lower():
            print(f"{i}: {line.strip().encode('ascii', 'ignore').decode('ascii')[:100]}")
