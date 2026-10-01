import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find `sync_single_contact(c):` block
# It starts at: def sync_single_contact(c):
# It ends at: return True, company_name, None (or similar)

def replace_conn_logic():
    # Replace the connection holding logic
    pass

# A simpler way is to just use string replacement for the parts holding the connection
old_code_1 = """        thread_conn = None
        try:
            thread_conn = database.get_db_connection()
            contact = thread_conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()"""

new_code_1 = """        thread_conn = None
        try:
            thread_conn = database.get_db_connection()
            contact = thread_conn.execute('SELECT * FROM contacts WHERE id = ?', (contact_id,)).fetchone()
            thread_conn.close() # Close immediately after read"""

content = content.replace(old_code_1, new_code_1)

old_code_2 = """            # Limit lists to prevent UI bloat
            final_products = final_products[:12]
            final_services = final_services[:12]
            
            thread_conn.execute('''"""

new_code_2 = """            # Limit lists to prevent UI bloat
            final_products = final_products[:12]
            final_services = final_services[:12]
            
            thread_conn = database.get_db_connection() # Reopen for writing
            thread_conn.execute('''"""

content = content.replace(old_code_2, new_code_2)

old_code_3 = """            logo_filename = download_company_logo(cleaned_website, contact_id, cleaned_company)
            if logo_filename:
                thread_conn.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
                
            thread_conn.commit()
            return True, company_name, None
            
        except Exception as e:
            if thread_conn:
                try: thread_conn.rollback()
                except: pass
            return False, company_name, str(e)
        finally:
            if thread_conn:
                try: thread_conn.close()
                except: pass"""

new_code_3 = """            logo_filename = download_company_logo(cleaned_website, contact_id, cleaned_company)
            if logo_filename:
                thread_conn.execute("UPDATE contacts SET company_logo = ? WHERE id = ?", (logo_filename, contact_id))
                
            thread_conn.commit()
            thread_conn.close()
            return True, company_name, None
            
        except Exception as e:
            if thread_conn:
                try: thread_conn.rollback()
                except: pass
            return False, company_name, str(e)
        finally:
            if thread_conn:
                try: thread_conn.close()
                except: pass"""

content = content.replace(old_code_3, new_code_3)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Scraper connection patched.")
