# How to Configure SMTP (Email Sending)

To allow the application to send real verification emails, you need to configure an SMTP server. The easiest way for testing is to use a **Gmail** account with an **App Password**.

---

## Step 1: Generate a Gmail App Password

> **Note:** Do NOT use your real Gmail password. You must generate a secure App Password.

1.  Go to your [Google Account Security Page](https://myaccount.google.com/security).
2.  Ensure **2-Step Verification** is turned **ON**.
3.  Under "How you sign in to Google", click on **2-Step Verification**, then scroll to the bottom and finding **App passwords**.
    *   *If you don't see it, search for "App passwords" in the search bar at the top.*
4.  Create a new App Password:
    *   **App name**: TrueGeoIP
    *   Click **Create**.
5.  Copy the 16-character password (it looks like `abcd efgh ijkl mnop`).

---

## Step 2: Configure the Application

1.  Open the `.env` file in your project folder (if you don't have one, create it).
2.  Add the following lines:

```ini
# SMTP Configuration (Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_FROM=your-email@gmail.com
```

*   Replace `your-email@gmail.com` with your actual Gmail address.
*   Replace `your-app-password-here` with the 16-character code you just copied.

---

## Step 3: Restart the Server

After saving the `.env` file, you must **restart** the server for changes to take effect.

```bash
# Stop the server (Ctrl+C)
# Start it again
python main.py
```
