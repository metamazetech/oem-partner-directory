with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

old_form = 'onsubmit="event.preventDefault(); uploadUpdateWithProgress();"'
new_form = 'onsubmit="document.getElementById(\'update-progress-container\').style.display=\'block\'; document.getElementById(\'update-progress-bar\').style.width=\'100%\'; document.getElementById(\'update-progress-bar\').style.animation=\'pulse 1.5s infinite\'; document.getElementById(\'update-progress-text\').innerText=\'Uploading and processing (this may take a minute)...\';"'

content = content.replace(old_form, new_form)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched admin.html')
