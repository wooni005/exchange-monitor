# Currency Exchange Monitor

A lightweight, self-hosted tool to monitor currency exchange rates, store history in SQLite, and receive alerts (Telegram/Email) when a new high record is broken within a configurable lookback period.

A full-stack exchange rate monitor that tracks the EUR/CZK rate using the Twelve Data API. It features a FastAPI backend with an SQLite database, a background scheduler for monthly high alerts, and a modern React dashboard with real-time charts.

## 📋 Features

* **Real-time Monitoring:** Checks exchange rates every 5 minutes.
* **Dynamic Record Tracking:** Detects records over a sliding window (e.g., 45 days).
* **Smart Alerts:** Sends Telegram and Email notifications only when a new high is reached.
* **Interactive Dashboard:** Visualizes price trends using Recharts.
* **Database Cleanup:** Automatically prunes data older than the lookback window to keep the system fast.
* **FastAPI Backend:** Modern, asynchronous API with lifespan management.
* **React Frontend:** Clean dashboard to visualize current rates and history.
* **Service-ready:** Configured to run as a systemd service on Linux.

---

## 🛠️ 1. Prerequisites (Installation)

### Update Node.js to v22

Since the frontend requires a modern Node version (v20+), install the LTS version:

1. `curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -`
2. `sudo apt-get install -y nodejs`
3. `node -v` (Verify it's v22.x)

### Python Setup

Ensure you have Python 3 and pip installed:

1. `sudo apt update`
2. `sudo apt install python3 python3-pip`
3. `pip3 install fastapi uvicorn httpx apscheduler emails dotenv`

---

## ⚙️ 2. Environment Configuration

### 2.1 Backend Configuration (FastAPI)

Create a `.env` file in the `monitor-api` directory. Use the following template and replace the placeholders with your actual credentials:

```ini
# --- Twelve Data API Configuration ---
# Get your free key at https://twelvedata.com
API_KEY="your_api_key_here"
SYMBOL="EUR/CZK"        # Can be any pair, e.g., USD/EUR, GBP/USD
LOOKBACK_DAYS=45       # Number of days to track for records

# --- Telegram Notification Settings ---
# BotFather gives you the token; userinfobot gives you the chat ID
TELEGRAM_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_chat_id"

# --- Email Alert Settings ---
# Use an 'App Password' for security (Gmail/Seznam/etc.)
EMAIL_USER="your_email@example.com"
EMAIL_PASSWORD="your_app_password"
SMTP_SERVER="smtp.yourprovider.com"
SMTP_PORT=587
EMAIL_RECEIVER="target_email@example.com"

# --- Application Settings ---
API_PORT=8000
DEBUG=False
```

### 2.2 Frontend Configuration (React/Vite)

The frontend needs to know where the API is running. Create a `.env.local` file in the `currency-ui` directory:

```ini
# Path: currency-ui/.env.local

# Replace with the IP address of your Raspberry Pi
VITE_API_BASE_URL=http://192.168.1.24:8000
```

---

## 🚀 3. Manual Startup (Development)

### Start Backend

`python3 monitor.py`
The API will be available at http://127.0.0.1:8000.

### Start Frontend

1. `cd currency-ui`
2. `npm install`
3. `npm run dev -- --host`
   The dashboard will be available at http://localhost:5173.

---

## 🛡️ 4. Production Deployment (Systemd Services)

### Build the Frontend

1. `cd currency-ui`
2. `npm run build`
3. `sudo npm install -g serve`

### Create Services

**1. Backend Service:** Create `/etc/systemd/system/currency-backend.service`

```ini
[Unit]
Description=FastAPI Currency Monitor
After=network.target

[Service]
User=arjan
WorkingDirectory=/home/arjan/your-project-path
ExecStart=/usr/bin/python3 monitor.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Frontend Service:** Create `/etc/systemd/system/currency-ui.service`

```ini
[Unit]
Description=Currency Monitor Frontend (Vite)
After=network.target

[Service]
# The user that runs the service
User=pi
# The directory where your package.json is located
WorkingDirectory=/home/pi/ssd/scripts/python/exchange-monitor/currency-ui
# Path to npm (check with 'which npm' if this fails)
ExecStart=/usr/bin/npm run dev -- --host
# Restart the service if it crashes
Restart=always
RestartSec=10
# Environment variables if needed
Environment=NODE_ENV=production

[Install]
WantedBy=multi-user.target
```

### Enable & Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable currency-backend currency-ui
sudo systemctl start currency-backend currency-ui
```

## 📊 5. Database & API Endpoints

The monitor automatically creates a local forex_monitor.db file on its first run.

`GET /`: Returns the latest rate and current monthly high.

`GET /history`: Returns the last 100 data points for the chart.

## 📝 License

This project is licensed under the **GPLv3 or later** - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer & Security Warning

This project is strictly intended for use within a private local network (LAN). It has not been audited for security and is not designed to be exposed directly to the public internet.

**Security Considerations:**

* No Authentication: The current API and UI do not feature a login system. Anyone on your network can access the dashboard.
* Development Servers: Running npm run dev or uvicorn with debug=True exposes detailed system information if an error occurs.
* Firewall: Ensure your router does not have port forwarding enabled for ports 8000 or 5173 to this device.

**Public Deployment:**
If you intend to make this accessible outside your home network, you must:

1. Implement an authentication layer (e.g., OAuth2 or Basic Auth).
2. Use a Production-grade web server like Nginx with HTTPS (SSL/TLS).
3. Disable all DEBUG flags in the .env file.
4. Run the Python backend using a production worker like gunicorn.

Use at your own risk. The authors are not responsible for any data loss or unauthorized access resulting from improper configuration.