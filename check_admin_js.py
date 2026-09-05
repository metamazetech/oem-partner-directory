with open('templates/admin.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_script = False
for line in lines:
    if '<script' in line:
        in_script = True
    if in_script:
        print(line.strip().encode('ascii', 'ignore').decode('ascii'))
    if '</script>' in line:
        in_script = False
