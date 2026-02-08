# Deployment Guide (Linux/Ubuntu)

This guide explains how to deploy the TrueGeoIP application to a production Linux server (e.g., DigitalOcean, AWS EC2, or a dedicated VM).

---

## 1. Prepare the Server

Connect to your server via SSH:
```bash
ssh user@your-server-ip
```

Update your package list and install Python and Nginx:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx -y
```

For a budget deployment, a VM with **6 GB RAM** can work if you use DB lookup mode (no full in-memory preload).

## 2. Transfer Files

You can use `git` (recommended) or `scp` to copy your files.

**Option A: Git**
```bash
git clone https://github.com/yourusername/your-repo.git /var/www/truegeoip
cd /var/www/truegeoip
```

**Option B: SCP (from your local machine)**
```bash
scp -r /path/to/project user@your-server-ip:/var/www/truegeoip
```

## 3. Application Setup

Navigate to your project directory and set up the virtual environment.

```bash
cd /var/www/truegeoip
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# One-time: build lookup indexes (important for low-RAM DB mode)
python3 scripts/build_lookup_indexes.py --db databasefull.sqlite
```

**Update `.env`**:
Create your `.env` file for production keys.
```bash
cp .env.example .env  # Or create new
nano .env
```

## 4. Systemd Service (Keep App Running)

Create a service file to manage the application process.

```bash
sudo nano /etc/systemd/system/truegeoip.service
```

Paste the following configuration:

```ini
[Unit]
Description=Gunicorn instance to serve TrueGeoIP
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/truegeoip
Environment="PATH=/var/www/truegeoip/venv/bin"
Environment="IP_DB_FILE=/var/www/truegeoip/databasefull.sqlite"
Environment="LOOKUP_MODE=db"
Environment="LOOKUP_WORKERS=4"
Environment="AUTO_CREATE_DB_INDEXES=0"
ExecStart=/var/www/truegeoip/venv/bin/gunicorn -w 1 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000 --timeout 120

[Install]
WantedBy=multi-user.target
```

Start and enable the service:
```bash
sudo systemctl start truegeoip
sudo systemctl enable truegeoip
```

Check status:
```bash
sudo systemctl status truegeoip
```

## 5. Nginx Configuration (Reverse Proxy)

Configure Nginx to sit in front of Gunicorn.

```bash
sudo nano /etc/nginx/sites-available/truegeoip
```

Paste the following:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com; # OR your server IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/truegeoip/static;
    }
}
```

Enable the site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/truegeoip /etc/nginx/sites-enabled/
sudo nginx -t  # Test for errors
sudo systemctl restart nginx
```

## 6. SSL (HTTPS) - Optional but Recommended

If you have a domain name, use Certbot to enable HTTPS.

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

## 7. Operational Commands

- **Restart App:** `sudo systemctl restart truegeoip`
- **View App Logs:** `journalctl -u truegeoip -f`
- **Nginx Logs:** `tail -f /var/log/nginx/error.log`
