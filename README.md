# OEM & Partner Directory Portal - Setup & Deployment Guide

This guide provides step-by-step instructions for deploying and running the OEM & Partner Relationship Directory Portal on **local development/production servers** and **cPanel Shared Hosting (using Passenger WSGI)**.

---

## 💻 Method 1: Local Server Installation (Windows / Linux / macOS)

Follow these steps to run the application on your local machine or an internal company server.

### 1. Prerequisites
Ensure you have the following installed:
* Python 3.8 or higher
* Git (optional, for version control)

### 2. Extract Files
Extract the zip archive (`oem_portal.zip`) into your target folder (e.g. `C:\oem-portal` or `/var/www/oem-portal`).

### 3. Create a Virtual Environment
Using a terminal, navigate to the folder and run:
* **Windows (Command Prompt / PowerShell)**:
  ```cmd
  python -m venv venv
  ```
* **Linux / macOS**:
  ```bash
  python3 -m venv venv
  ```

### 4. Activate Virtual Environment
* **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
* **Windows (CMD)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
* **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### 5. Install Dependencies
Install all required libraries using pip:
```bash
pip install -r requirements.txt
```

### 6. Run the Application
Start the development server:
```bash
python app.py
```
By default, the server runs on all interfaces (`0.0.0.0`) on port **5000**.
* Open **`http://localhost:5000`** in your browser.
* Other devices on your local network can access it using your computer's IP address (e.g. `http://192.168.1.xxx:5000`).

---

## ☁️ Method 2: Deployment on cPanel Shared Hosting (via Passenger WSGI)

Most modern cPanel hostings support Python via **Passenger WSGI**.

### Step 1: Upload Files
1. Log in to your cPanel.
2. Open **File Manager** and create a directory for your app outside the `public_html` root (e.g., `/home/username/oem_portal`).
3. Upload and extract **`oem_portal.zip`** in this directory.

### Step 2: Create Python Application in cPanel
1. Navigate to the cPanel dashboard and search for **"Setup Python App"**.
2. Click **"Create Application"**.
3. Fill out the application settings:
   * **Python Version**: Select `3.8`, `3.9`, or higher.
   * **Application Mode**: Select `Production`.
   * **Application Root**: Enter the folder name relative to home (e.g., `oem_portal`).
   * **Application URL**: Select your domain/subdomain and specify the subpath. For example, if you want your portal to run at `https://yourdomain.com/oemportal`, select your domain and enter `oemportal` in the text box. All internal page links are rendered relative to this path automatically.
   * **Application Startup File**: Enter `passenger_wsgi.py`.
   * **Application Entry Point**: Enter `application` (all lowercase).
4. Click **"Create"**.

### Step 3: Install Requirements
1. Copy the command shown at the top of the Setup Python App page (e.g., `source /home/username/nodevenv/oem_portal/.../activate`).
2. Log in to your server via SSH (or use the cPanel **"Terminal"** tool).
3. Paste the activation command and press Enter. This activates your app's virtual environment.
4. Run the pip installer:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Step 4: Configure the WSGI Entry Point
The application includes a `passenger_wsgi.py` file pre-configured for cPanel. It automatically imports the Flask app object and runs it as the WSGI `application` callable:
```python
import os
import sys

# Insert app directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import app object as application for WSGI
from app import app as application
```
Ensure your database file `oem_tracker.db` and the `uploads` directory have read/write permissions for the server process (typically `755` or `777`).

### Step 5: Zero-Downtime Reloads (tmp/restart.txt)
To reload or restart the application after uploading new files, you do not need to log into the cPanel GUI:
1. Simply touch or upload the **`tmp/restart.txt`** file in your application root folder (included inside the release zip).
2. Passenger WSGI monitors this file's modification timestamp and will automatically recycle the running process and reload the latest Python code on the next page request.
3. If the automatic restart does not trigger, go back to the cPanel **"Setup Python App"** page and click **"Restart"** on your application.

---

## 🎨 Administrator Whitelabel Customization
Once installed:
1. Log in as an **admin** user.
2. Navigate to the **Admin Panel** from the sidebar.
3. Under the **Whitelabel Branding & Customization** card:
   * Edit the portal name.
   * Upload your custom logo image.
   * Upload your custom favicon.
4. Click **Save Settings** to apply the branding globally.

---

*Portal is developed by [Metamaze Private Limited](https://metamaze.co.in)*  
*Email:* it@metamaze.co.in
