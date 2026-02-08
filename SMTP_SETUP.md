# How to Configure Email Sending

To send real verification emails, configure at least one email provider.

Recommended: **Resend** (transactional email, production-style)  
Fallback: **SMTP** (for example Gmail App Password)

---

## Option A (Recommended): Resend

1. Create a Resend account and generate an API key.
2. Open `.env` and add:

```ini
EMAIL_PROVIDER=auto
RESEND_API_KEY=your-resend-api-key-here
RESEND_FROM=onboarding@resend.dev
```

---

## Option B: SMTP (Gmail)

> Do NOT use your real Gmail password. Use a generated App Password.

1. Go to your Google Account Security page.
2. Enable 2-Step Verification.
3. Create an App Password and copy it.
4. Open `.env` and add:

```ini
EMAIL_PROVIDER=auto
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here
SMTP_FROM=your-email@gmail.com
```

---

## Final Step: Restart the Server

After saving the `.env` file, you must **restart** the server for changes to take effect.

```bash
# Stop the server (Ctrl+C)
# Start it again
python main.py
```
