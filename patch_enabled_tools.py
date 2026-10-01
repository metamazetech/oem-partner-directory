import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For the cached block:
old_cached_dict = """        return dict(
            oem_groups=cached['groups'], 
            portal_settings=cached['settings'], 
            theme=user_theme, 
            custom_theme_colors=custom_theme_colors,
            useful_websites=cached['useful_websites'],
            change_logs=cached['change_logs'],
            csrf_token=session.get('csrf_token', ''),
            role=session.get('role')
        )"""

new_cached_dict = """        return dict(
            oem_groups=cached['groups'], 
            portal_settings=cached['settings'], 
            theme=user_theme, 
            custom_theme_colors=custom_theme_colors,
            useful_websites=cached['useful_websites'],
            change_logs=cached['change_logs'],
            csrf_token=session.get('csrf_token', ''),
            role=session.get('role'),
            enabled_tools=cached['settings'].get('enabled_work_tools', 'unit,currency,calculator,cctv,power,pdf').split(',')
        )"""

content = content.replace(old_cached_dict, new_cached_dict)

# For the un-cached block:
old_dict = """    return dict(
        oem_groups=groups, 
        portal_settings=settings, 
        theme=user_theme, 
        custom_theme_colors=custom_theme_colors,
        useful_websites=useful_websites,
        change_logs=change_logs,
        csrf_token=session.get('csrf_token', ''),
        role=session.get('role')
    )"""

new_dict = """    return dict(
        oem_groups=groups, 
        portal_settings=settings, 
        theme=user_theme, 
        custom_theme_colors=custom_theme_colors,
        useful_websites=useful_websites,
        change_logs=change_logs,
        csrf_token=session.get('csrf_token', ''),
        role=session.get('role'),
        enabled_tools=settings.get('enabled_work_tools', 'unit,currency,calculator,cctv,power,pdf').split(',')
    )"""

content = content.replace(old_dict, new_dict)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added enabled_tools to context processor")
