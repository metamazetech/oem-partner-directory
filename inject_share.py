import re

with open('templates/contact_detail.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_header = '''<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                            <h2 class="card-title" style="margin-bottom:0;">👥 Team Contacts</h2>
                            {% if contact_persons %}
                            <button class="btn btn-secondary btn-sm" onclick="shareAllContacts()" style="padding: 0.35rem 0.75rem; font-size: 0.75rem; display:flex; align-items:center; gap:0.4rem;">
                                <span>🔗</span> Share All
                            </button>
                            {% endif %}
                        </div>'''

content = content.replace('<h2 class="card-title">👥 Team Contacts</h2>', new_header)

js_script = '''
    <script>
    function shareAllContacts() {
        let text = "{{ contact['company_name'] }} - Team Contacts\\n\\n";
        
        {% for person in contact_persons %}
        text += "👤 {{ person['name'] }}\\n";
        text += "💼 {{ person['designation'] or 'Pre-Sales Contact' }}\\n";
        {% if person['phone'] %}text += "📞 {{ person['phone'] }}\\n";{% endif %}
        {% if person['email'] %}text += "✉️ {{ person['email'] }}\\n";{% endif %}
        text += "\\n";
        {% endfor %}
        
        if (navigator.share) {
            navigator.share({
                title: '{{ contact['company_name'] }} Contacts',
                text: text
            }).catch(console.error);
        } else {
            navigator.clipboard.writeText(text).then(() => {
                alert("Contacts copied to clipboard!");
            }).catch(err => {
                alert("Failed to copy contacts.");
                console.error(err);
            });
        }
    }
    </script>
'''

if 'shareAllContacts' not in content:
    content = content.replace('</body>', js_script + '\n</body>')

with open('templates/contact_detail.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
