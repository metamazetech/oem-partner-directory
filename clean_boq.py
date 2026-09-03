import re

with open('boq_out.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# strip out emojis for printing
import emoji
text = emoji.replace_emoji(text, replace='')
with open('boq_out_clean.txt', 'w', encoding='utf-8') as f:
    f.write(text.encode('ascii', 'ignore').decode('ascii'))
