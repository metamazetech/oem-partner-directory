import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import unittest.mock
import io
from app import app, database

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Ensure database is initialized
        database.init_db()

    def test_anonymous_root_redirect(self):
        # Accessing root / should redirect anonymous users to login page
        response = self.app.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('login' in response.location)

    def test_work_tools_view(self):
        # Work tools view should be publicly accessible (200 OK)
        response = self.app.get('/work-tools')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Portal Work Tools', response.data)
        self.assertIn(b'Unit Converter', response.data)
        self.assertIn(b'Currency Calculator', response.data)
        self.assertIn(b'Cloud Infrastructure Comparative Calculator', response.data)

    def test_currency_rates_sync(self):
        # Syncing rates should execute successfully
        response = self.app.post('/work-tools/update-rates', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'exchange rates', response.data)

    def test_pdf_conversion_word(self):
        # Generate a valid PDF in memory
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        pdf_io = io.BytesIO()
        writer.write(pdf_io)
        pdf_bytes = pdf_io.getvalue()

        data = {
            'pdf_file': (io.BytesIO(pdf_bytes), 'test.pdf'),
            'format': 'word'
        }
        response = self.app.post('/work-tools/convert-pdf', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/msword')
        self.assertTrue(response.headers['Content-disposition'].startswith('attachment;'))

    def test_pdf_conversion_excel(self):
        # Generate a valid PDF in memory
        from pypdf import PdfWriter
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        pdf_io = io.BytesIO()
        writer.write(pdf_io)
        pdf_bytes = pdf_io.getvalue()

        data = {
            'pdf_file': (io.BytesIO(pdf_bytes), 'test.pdf'),
            'format': 'excel'
        }
        response = self.app.post('/work-tools/convert-pdf', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')

if __name__ == '__main__':
    unittest.main()
