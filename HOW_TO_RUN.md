# How to Run the TrueGeoIP Project

This is a comprehensive guide to setting up, configuring, and running the TrueGeoIP application.

---

## 1. Prerequisites

Ensure you have **Python 3.9+** installed.

### Install Dependencies
Run the following command to install all required packages:

```bash
pip install -r requirements.txt
```
*(If `requirements.txt` doesn't exist, use this command)*:
```bash
pip install fastapi uvicorn[standard] jinja2 aiosqlite authlib itsdangerous python-dotenv passlib[bcrypt] httpx python-multipart
```

---

## 2. Configuration (.env)

The application requires a `.env` file for security and OAuth.

1.  Open the file `.env` in the project root.
2.  **Required**: Update the Google OAuth credentials.

```ini
# .env file content
SECRET_KEY=... (keep the generated one)

# GOOGLE OAUTH CREDENTIALS
# Create these at: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here

# EMAIL DELIVERY (required for real verification emails)
EMAIL_PROVIDER=auto
RESEND_API_KEY=your-resend-api-key-here
RESEND_FROM=onboarding@resend.dev
```

> **Note**: If you skip this, "Sign in with Google" will fail, but you can still use email/password sign up.
>  
> **Email note**: If `RESEND_API_KEY` (or SMTP credentials) is missing, verification falls back to debug mode and no real email is sent.

---

## 3. Running the Application

To start the server, verify you are in the project folder and run:

```bash
python main.py
```

-   **Wait ~60 seconds**: The server loads large datasets into memory at startup.
-   Access the app: **[http://127.0.0.1:8000](http://127.0.0.1:8000)** (Recommended to avoid IPv6 issues)

---

## 4. Troubleshooting

### Blank Page / Connection Error at `localhost`
Use `127.0.0.1` instead of `localhost`.
Visit: **[http://127.0.0.1:![alt text](image.png)8000](http://127.0.0.1:8000)**

### Error: `[Errno 48] Address already in use`
This means the server is **already running** in the background or another process is using port 8000.

**Fix (Mac/Linux):**
Run this command to find and kill the process:
```bash
lsof -ti:8000 | xargs kill -9
```
Then try running `python main.py` again.

### Error: `ModuleNotFoundError`
You are missing a dependency. Run the install command in Step 1 again.

### Google Sign-In Error: `OAuthError: mismatch_redirect_uri`
Ensure your Google Cloud Console redirect URI matches exactly:
`http://localhost:8000/auth/google/callback`

---

## 5. Features
-   **Public IP Lookup**: `http://127.0.0.1:8000/`
-   **User Accounts**: Sign Up/In with Email or Google.
-   **Contact Page**: `http://127.0.0.1:8000/contact`
-   **Pricing Page**: `http://127.0.0.1:8000/pricing`
-   **API**: `http://127.0.0.1:8000/api/check?ip=8.8.8.8`
