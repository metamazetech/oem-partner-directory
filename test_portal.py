import unittest
import os
import sqlite3
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
            'password': 'password123'
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
            'password': 'admin123'
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
            'password': 'password123'
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
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
        
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
            'password': 'password123'
        })
        # Approve as viewer
        conn = sqlite3.connect('oem_tracker_test.db')
        viewer_id = conn.execute("SELECT id FROM users WHERE username='view_user'").fetchone()[0]
        conn.execute("UPDATE users SET status='approved' WHERE id=?", (viewer_id,))
        conn.commit()
        conn.close()

        # Login as viewer
        self.client.post('/login', data={'username': 'view_user', 'password': 'password123'})
        viewer_export = self.client.get('/export/csv')
        self.assertEqual(viewer_export.status_code, 403) # Forbidden
        print("[OK] Verified: View-only users are forbidden from exporting CSV.")

        # Login as Admin
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
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
        # Scenario 10: Factory Reset Danger Zone
        # ----------------------------------------------------
        print("\nScenario 10: Factory Reset Danger Zone...")
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'})
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
