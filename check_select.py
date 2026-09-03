with open('templates/rfp_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

# find all selects
import re
for match in re.finditer(r'<select.*?>', content):
    start = max(0, match.start() - 100)
    end = min(len(content), match.end() + 200)
    print(content[start:end])
    print('---')
