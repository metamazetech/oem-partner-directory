import unittest
import os
import sqlite3
import json
from app import app
import database

class PortalTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Fresh test database setup
        database.DB_PATH = 'oem_tracker_test.db'
        # Override DB path in app's database references
        import app as portal_app
        portal_app.database.DB_PATH = 'oem_tracker_test.db'
        
        # Remove old test DB if exists
        if os.path.exists('oem_tracker_test.db'):
            os.remove('oem_tracker_test.db')
            
        database.init_db()
        
    def tearDown(self):
        # Clean up database
        if os.path.exists('oem_tracker_test.db'):
            os.remove('oem_tracker_test.db')

    def test_complete_portal_workflow(self):
        print("\n=== STARTING SCENARIO-BASED PORTAL TESTING ===")

        # ----------------------------------------------------
        # Scenario 1: User Registration Defaulting to Viewer
        # ----------------------------------------------------
        print("\nScenario 1: User Registration Request...")
        reg_response = self.client.post('/register', data={
            'username': 'sales_manager',
            'email': 'manager@company.com',
            'password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(reg_response.status_code, 200)
        self.assertIn(b"Registration request submitted", reg_response.data)

        # Verify role is viewer and status is pending in DB
        conn = sqlite3.connect('oem_tracker_test.db')
        user = conn.execute("SELECT * FROM users WHERE username='sales_manager'").fetchone()
        conn.close()
        self.assertIsNotNone(user)
        self.assertEqual(user[4], 'viewer') # Role index 4 (0-indexed)
        self.assertEqual(user[5], 'pending') # Status index 5 (0-indexed)
        print("[OK] Verified: New user registration role is viewer and status is pending.")

        # ----------------------------------------------------
        # Scenario 2: Admin Login
        # ----------------------------------------------------
        print("\nScenario 2: Admin Login...")
        login_response = self.client.post('/login', data={
            'username': 'admin',
            'password': '@Admin#99!Directory'
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b"OEM & Distributor Directory", login_response.data)
        print("[OK] Verified: Admin logged in successfully.")

        # ----------------------------------------------------
        # Scenario 3: Admin Approving Pending User & Setting Role
        # ----------------------------------------------------
        print("\nScenario 3: Admin User Management...")
        # Get pending user id
        conn = sqlite3.connect('oem_tracker_test.db')
        user_id = conn.execute("SELECT id FROM users WHERE username='sales_manager'").fetchone()[0]
        conn.close()

        # Approve the user first
        approve_status_response = self.client.post(f'/admin/approve/{user_id}', follow_redirects=True)
        self.assertEqual(approve_status_response.status_code, 200)

        # Update role to user (Manager)
        approve_role_response = self.client.post(f'/admin/user/{user_id}/update', data={
            'role': 'user', # Upgrade to Manager/Engineer
            'allowed_groups': 'All'
        }, follow_redirects=True)
        self.assertEqual(approve_role_response.status_code, 200)
        
        # Verify approval in DB
        conn = sqlite3.connect('oem_tracker_test.db')
        user = conn.execute("SELECT role, status FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        self.assertEqual(user[0], 'user')
        self.assertEqual(user[1], 'approved')
        print("[OK] Verified: Admin updated status to approved and upgraded role to manager.")

        # Logout Admin
        self.client.get('/logout')

        # ----------------------------------------------------
        # Scenario 4: User Login after approval
        # ----------------------------------------------------
        print("\nScenario 4: Approved User Login...")
        login_response = self.client.post('/login', data={
            'username': 'sales_manager',
            'password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b"OEM & Distributor Directory", login_response.data)
        print("[OK] Verified: Approved manager can now login.")

        # ----------------------------------------------------
        # Scenario 5: Category & Partner Operations
        # ----------------------------------------------------
        print("\nScenario 5: Creating Category & Adding Partner...")
        # Add category
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': '@Admin#99!Directory'})
        
        cat_response = self.client.post('/admin/category/add', data={
            'name': 'Cybersecurity',
            'icon': 'Icon'
        }, follow_redirects=True)
        self.assertEqual(cat_response.status_code, 200)
        
        # Verify category exists
        conn = sqlite3.connect('oem_tracker_test.db')
        cat = conn.execute("SELECT * FROM oem_groups WHERE name='Cybersecurity'").fetchone()
        conn.close()
        self.assertIsNotNone(cat)
        print("[OK] Verified: Custom category 'Cybersecurity' created successfully.")

        # Add partner manually
        partner_response = self.client.post('/contact/add', data={
            'company_name': 'Palo Alto Networks',
            'type': 'OEM',
            'group_name': 'Cybersecurity',
            'website': 'https://paloaltonetworks.com',
            'address': 'Santa Clara, CA',
            'contact_name[]': ['Alice Smith'],
            'contact_designation[]': ['Sales Engineer'],
            'contact_email[]': ['alice@paloalto.com'],
            'contact_phone[]': ['+1-408-555-0199']
        }, follow_redirects=True)
        self.assertEqual(partner_response.status_code, 200)

        # Verify partner exists
        conn = sqlite3.connect('oem_tracker_test.db')
        partner = conn.execute("SELECT * FROM contacts WHERE company_name='Palo Alto Networks'").fetchone()
        conn.close()
        self.assertIsNotNone(partner)
        self.assertEqual(partner[2], 'Palo Alto Networks')
        self.assertEqual(partner[4], 'Cybersecurity') # Group
        print("[OK] Verified: Partner profile added successfully with contacts.")

        # Test Fetch Logo Endpoint
        partner_id = partner[0]
        fetch_logo_response = self.client.post(f'/contact/{partner_id}/fetch-logo', follow_redirects=True)
        self.assertIn(fetch_logo_response.status_code, [200, 400])
        print("[OK] Verified: Partner fetch-logo endpoint executed safely.")

        # Test Scan Card Endpoint
        scan_response = self.client.post('/scan-card', follow_redirects=True)
        self.assertEqual(scan_response.status_code, 400)
        print("[OK] Verified: Scan card endpoint handles empty payloads securely.")

        # ----------------------------------------------------
        # Scenario 6: Log Interactions & Follow-ups
        # ----------------------------------------------------
        print("\nScenario 6: Logging Interaction & Creating Reminder...")
        partner_id = partner[0]
        interaction_response = self.client.post(f'/contact/{partner_id}/interaction', data={
            'interaction_date': '2026-07-15',
            'type_call': 'Call',
            'summary': 'Introductory sync with Alice',
            'next_steps': 'Schedule product demo',
            'followup_date': '2026-07-20'
        }, follow_redirects=True)
        self.assertEqual(interaction_response.status_code, 200)

        # Verify interaction exists
        conn = sqlite3.connect('oem_tracker_test.db')
        interaction = conn.execute("SELECT * FROM interactions WHERE contact_id=?", (partner_id,)).fetchone()
        conn.close()
        self.assertIsNotNone(interaction)
        self.assertEqual(interaction[5], 'Introductory sync with Alice')
        self.assertEqual(interaction[7], '2026-07-20') # Followup date
        print("[OK] Verified: Logged sales interaction and set follow-up task reminder.")

        # ----------------------------------------------------
        # Scenario 7: CSV Exports Permissions (Viewer vs Admin)
        # ----------------------------------------------------
        print("\nScenario 7: Checking CSV Export Security Controls...")
        # Create a view-only user
        self.client.get('/logout')
        self.client.post('/register', data={
            'username': 'view_user',
            'email': 'viewer@company.com',
            'password': 'Password@123'
        })
        # Approve as viewer
        conn = sqlite3.connect('oem_tracker_test.db')
        viewer_id = conn.execute("SELECT id FROM users WHERE username='view_user'").fetchone()[0]
        conn.execute("UPDATE users SET status='approved' WHERE id=?", (viewer_id,))
        conn.commit()
        conn.close()

        # Login as viewer
        self.client.post('/login', data={'username': 'view_user', 'password': 'Password@123'})
        viewer_export = self.client.get('/export/csv')
        self.assertEqual(viewer_export.status_code, 403) # Forbidden
        print("[OK] Verified: View-only users are forbidden from exporting CSV.")

        # Login as Admin
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': '@Admin#99!Directory'})
        admin_export = self.client.get('/export/csv')
        self.assertEqual(admin_export.status_code, 200) # Success
        self.assertIn('text/csv', admin_export.content_type)
        print("[OK] Verified: Admin users can export CSV.")

        # ----------------------------------------------------
        # Scenario 8: Whitelabel Settings Customization
        # ----------------------------------------------------
        print("\nScenario 8: Whitelabel Configurations...")
        wl_response = self.client.post('/admin/settings/update', data={
            'portal_name': 'NextNode Systems Portal'
        }, follow_redirects=True)
        self.assertEqual(wl_response.status_code, 200)

        # Verify portal settings value
        conn = sqlite3.connect('oem_tracker_test.db')
        wl = conn.execute("SELECT value FROM portal_settings WHERE key='portal_name'").fetchone()[0]
        conn.close()
        self.assertEqual(wl, 'NextNode Systems Portal')
        print("[OK] Verified: Whitelabel branding name successfully customized.")

        # ----------------------------------------------------
        # Scenario 9: Forgot Password & Simulation mail
        # ----------------------------------------------------
        print("\nScenario 9: Forgot Password simulation...")
        # Toggle forgot password link
        self.client.post('/admin/email-settings/update', data={
            'forgot_password_enabled': 'true',
            'email_service_type': 'smtp',
            'email_server': 'smtp.gmail.com',
            'email_port': '587',
            'email_ssl': 'true',
            'email_username': 'alerts@nextnode.com',
            'email_password': 'supersecretpass'
        })
        self.client.get('/logout')
        
        fp_response = self.client.post('/forgot-password', data={
            'email': 'manager@company.com'
        }, follow_redirects=True)
        self.assertEqual(fp_response.status_code, 200)
        self.assertIn(b"Password recovery details sent", fp_response.data)
        print("[OK] Verified: Password recovery requested and simulated mail logs created.")

        # ----------------------------------------------------
        # Scenario 9.5: Direct User Creation, Master Sync, and Backup
        # ----------------------------------------------------
        print("\nScenario 9.5: Testing User Creation, Master Sync, and Backup...")
        # Login as Admin
        self.client.post('/login', data={'username': 'admin', 'password': '@Admin#99!Directory'})
        
        # Test Direct User Creation
        create_user_resp = self.client.post('/admin/user/create', data={
            'username': 'newadminuser',
            'email': 'newadmin@presales-tracker.local',
            'password': '@Password#99!Strong',
            'role': 'admin'
        }, follow_redirects=True)
        self.assertEqual(create_user_resp.status_code, 200)
        
        # Verify user is in db
        conn = sqlite3.connect('oem_tracker_test.db')
        user_exist = conn.execute("SELECT id FROM users WHERE username='newadminuser'").fetchone()
        conn.close()
        self.assertIsNotNone(user_exist)
        print("[OK] Verified: Admin user account successfully created directly with strong password.")
        
        # Test Master Sync
        master_sync_resp = self.client.post('/admin/refresh-all-contacts', follow_redirects=True)
        self.assertEqual(master_sync_resp.status_code, 200)
        print("[OK] Verified: Master sync offerings refresh route executed successfully.")
        
        # Test Master Backup Download
        backup_resp = self.client.get('/admin/backup/download')
        self.assertEqual(backup_resp.status_code, 200)
        self.assertEqual(backup_resp.content_type, 'application/zip')
        print("[OK] Verified: Master backup ZIP download generated successfully.")

        # ----------------------------------------------------
        # Scenario 9.7: Testing Multiple Contacts CSV Import & Merge
        # ----------------------------------------------------
        print("\nScenario 9.7: Testing Multiple Contacts CSV Import & Merge...")
        
        # Prepare mock CSV payload with duplicate company rows (different contact persons)
        csv_data = (
            "Company Name,Type,OEM Group,Website,Address,Primary Contact Name,Primary Designation,Primary Email,Primary Phone\n"
            "Fortinet,OEM,Security,fortinet.com,Sunnyvale,John Forti,Manager,john@fortinet.com,11111\n"
            "Fortinet,OEM,Security,fortinet.com,Sunnyvale,Sarah Net,Engineer,sarah@fortinet.com,22222\n"
        )
        
        import io
        response = self.client.post('/import/csv', data={
            'csv_file': (io.BytesIO(csv_data.encode('utf-8')), 'test_import.csv')
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify both contacts exist under the same Fortinet partner record
        conn = sqlite3.connect('oem_tracker_test.db')
        fortinet_record = conn.execute("SELECT contact_persons FROM contacts WHERE company_name='Fortinet'").fetchone()
        conn.close()
        
        self.assertIsNotNone(fortinet_record)
        persons = json.loads(fortinet_record[0])
        self.assertEqual(len(persons), 2)
        self.assertEqual(persons[0]['name'], 'John Forti')
        self.assertEqual(persons[1]['name'], 'Sarah Net')
        print("[OK] Verified: CSV Import successfully merged duplicate company rows into secondary Team Contacts.")

        # ----------------------------------------------------
        # Scenario 9.9: Testing OEM News Feed & Sync
        # ----------------------------------------------------
        print("\nScenario 9.9: Testing OEM News Feed & Sync...")
        
        # Test loading news page
        news_page_resp = self.client.get('/news')
        self.assertEqual(news_page_resp.status_code, 200)
        self.assertIn(b'OEM News', news_page_resp.data)
        
        # Test manual news fetch
        news_fetch_resp = self.client.post('/news/fetch', follow_redirects=True)
        self.assertEqual(news_fetch_resp.status_code, 200)
        
        conn = sqlite3.connect('oem_tracker_test.db')
        news_count = conn.execute("SELECT COUNT(*) FROM oem_news").fetchone()[0]
        conn.close()
        print(f"[OK] Verified: OEM News routes executed safely. News count in DB: {news_count}")

        # ----------------------------------------------------
        # Scenario 9.95: Testing RFP Section Features
        # ----------------------------------------------------
        print("\nScenario 9.95: Testing RFP Section Features...")
        
        # 1. Access RFP List Page
        rfps_page_resp = self.client.get('/rfps')
        self.assertEqual(rfps_page_resp.status_code, 200)
        self.assertIn(b'RFP Procurement Opportunities', rfps_page_resp.data)
        
        # 2. Create RFP
        rfp_payload = {
            'rfp_number': 'GEM/2026/B/99981',
            'pre_bid_date': '2026-08-15',
            'submission_date': '2026-08-30',
            'contact_name': 'Key Contact Person',
            'contact_phone': '9988776655',
            'contact_email': 'contact@client.gov.in',
            'contact_address': 'Procurement Department'
        }
        create_rfp_resp = self.client.post('/rfps/create', data=rfp_payload, follow_redirects=True)
        self.assertEqual(create_rfp_resp.status_code, 200)
        self.assertIn(b'Workspace for managing matrix comparisons', create_rfp_resp.data)
        
        # Verify in DB and pre-seeded checklist
        conn = sqlite3.connect('oem_tracker_test.db')
        rfp_row = conn.execute("SELECT id FROM rfps WHERE rfp_number = 'GEM/2026/B/99981'").fetchone()
        self.assertIsNotNone(rfp_row)
        rfp_id = rfp_row[0]
        
        checklist_count = conn.execute("SELECT COUNT(*) FROM rfp_checklist WHERE rfp_id = ?", (rfp_id,)).fetchone()[0]
        self.assertEqual(checklist_count, 5) # Should pre-seed 5 items
        conn.close()
        print("[OK] Verified: RFP created and 5 checklist items pre-seeded successfully.")
        
        # 3. Save BoQ OEM Matrix
        boq_payload = {
            'items': [
                {
                    'item_name': 'Next-Gen Firewall',
                    'quantity': 2,
                    'mappings': {
                        'Cisco': {'model': 'Firepower 1010', 'remarks': 'Include licenses'},
                        'Fortinet': 'FortiGate 60F'
                    }
                },
                {
                    'item_name': 'Core Switch',
                    'quantity': 4,
                    'mappings': {
                        'Cisco': {'model': 'Catalyst 9300', 'remarks': 'Include stacking cables'}
                    }
                }
            ]
        }
        save_boq_resp = self.client.post(f'/rfps/{rfp_id}/save-boq', json=boq_payload)
        self.assertEqual(save_boq_resp.status_code, 200)
        
        # Verify in DB
        conn = sqlite3.connect('oem_tracker_test.db')
        boq_count = conn.execute("SELECT COUNT(*) FROM rfp_boq_items WHERE rfp_id = ?", (rfp_id,)).fetchone()[0]
        self.assertEqual(boq_count, 2)
        
        # Check mapping count
        mapping_count = conn.execute("""
            SELECT COUNT(*) FROM rfp_boq_oem_mappings m
            JOIN rfp_boq_items i ON m.boq_item_id = i.id
            WHERE i.rfp_id = ?
        """, (rfp_id,)).fetchone()[0]
        self.assertEqual(mapping_count, 3) # 2 mappings for item 1, 1 mapping for item 2
        
        # Check remarks column values
        remarks_list = conn.execute("""
            SELECT remarks FROM rfp_boq_oem_mappings m
            JOIN rfp_boq_items i ON m.boq_item_id = i.id
            WHERE i.rfp_id = ? AND m.oem_name = 'Cisco'
            ORDER BY i.id
        """, (rfp_id,)).fetchall()
        self.assertEqual(remarks_list[0][0], 'Include licenses')
        self.assertEqual(remarks_list[1][0], 'Include stacking cables')
        conn.close()
        print("[OK] Verified: BoQ OEM Matrix details and remarks saved and retrieved successfully.")
        
        # 4. Toggle Checklist Item Status
        conn = sqlite3.connect('oem_tracker_test.db')
        checklist_item = conn.execute("SELECT id, status FROM rfp_checklist WHERE rfp_id = ?", (rfp_id,)).fetchone()
        item_id, current_status = checklist_item[0], checklist_item[1]
        conn.close()
        
        toggle_resp = self.client.post(f'/rfps/{rfp_id}/checklist/{item_id}/toggle')
        self.assertEqual(toggle_resp.status_code, 200)
        toggle_data = json.loads(toggle_resp.data)
        self.assertEqual(toggle_data['new_status'], 'Received')
        print("[OK] Verified: Document Checklist toggling AJAX handler updates successfully.")
        
        # 5. File Upload Size Limits
        # Verify we can upload file
        import io
        small_file = (io.BytesIO(b"dummy document content"), "tender.pdf")
        upload_resp = self.client.post(f'/rfps/{rfp_id}/upload', data={
            'doc_type': 'rfp',
            'file': small_file
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(upload_resp.status_code, 200)
        self.assertIn(b"tender.pdf", upload_resp.data)
        
        # Verify size limit warning for file larger than 40 MB
        large_content = b"0" * (41 * 1024 * 1024) # 41 MB
        large_file = (io.BytesIO(large_content), "large.zip")
        upload_large_resp = self.client.post(f'/rfps/{rfp_id}/upload', data={
            'doc_type': 'rfp',
            'file': large_file
        }, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(upload_large_resp.status_code, 200)
        self.assertIn(b"exceeds 40 MB limit", upload_large_resp.data)
        print("[OK] Verified: File upload size constraints (40MB limit filters) are fully functional.")
        
        # 6. Universal Search Queries
        search_match_resp = self.client.get('/rfps?search=99981')
        self.assertEqual(search_match_resp.status_code, 200)
        self.assertIn(b'GEM/2026/B/99981', search_match_resp.data)
        
        # Search by BoQ item
        search_boq_resp = self.client.get('/rfps?search=Firewall')
        self.assertEqual(search_boq_resp.status_code, 200)
        self.assertIn(b'GEM/2026/B/99981', search_boq_resp.data)
        
        # Search by checklist item
        search_checklist_resp = self.client.get('/rfps?search=Authorization')
        self.assertEqual(search_checklist_resp.status_code, 200)
        self.assertIn(b'GEM/2026/B/99981', search_checklist_resp.data)
        
        # Search for non-existent item
        search_empty_resp = self.client.get('/rfps?search=nonexistentterm')
        self.assertEqual(search_empty_resp.status_code, 200)
        self.assertNotIn(f'href="/rfps/{rfp_id}"'.encode(), search_empty_resp.data)
        print("[OK] Verified: Universal search correctly matches RFP numbers, BoQ specifications, and checklist items.")

        # ----------------------------------------------------
        # Scenario 10: Factory Reset Danger Zone
        # ----------------------------------------------------
        print("\nScenario 10: Factory Reset Danger Zone...")
        self.client.post('/login', data={'username': 'admin', 'password': '@Admin#99!Directory'})
        reset_response = self.client.post('/admin/reset-portal', follow_redirects=True)
        self.assertEqual(reset_response.status_code, 200)

        # Verify tables are empty
        conn = sqlite3.connect('oem_tracker_test.db')
        contacts_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        interactions_count = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
        groups_count = conn.execute("SELECT COUNT(*) FROM oem_groups").fetchone()[0]
        conn.close()
        self.assertEqual(contacts_count, 0)
        self.assertEqual(interactions_count, 0)
        self.assertEqual(groups_count, 0)
        print("[OK] Verified: Factory Reset successfully cleared directory tables.")
        
        print("\n=== ALL SCENARIOS COMPLETED SUCCESSFULLY ===")

if __name__ == '__main__':
    unittest.main()
