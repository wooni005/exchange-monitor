# 🚀 EUR/CZK Currency Monitor & Dashboard

A full-stack exchange rate monitor that tracks the EUR/CZK rate using the Twelve Data API. It features a FastAPI backend with an SQLite database, a background scheduler for monthly high alerts, and a modern React dashboard with real-time charts.

## 📋 Features
* **Real-time Monitoring:** Checks exchange rates every 5 minutes.
* **Monthly High Alerts:** Sends Telegram and Email notifications when a new record is set.
* **Interactive Dashboard:** Visualizes price trends using Recharts.
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
3. `pip3 install fastapi uvicorn httpx apscheduler emails`

---

## ⚙️ 2. Configuration

### Backend (monitor.py)
Replace the following placeholders in your script with your own credentials:
* **API_KEY**: Your Twelve Data API key.
* **TELEGRAM_TOKEN** & **TELEGRAM_CHAT_ID**: Your bot credentials from BotFather.
* **EMAIL_USER** & **EMAIL_PASSWORD**: Your SMTP details (use App Passwords for Gmail).
* **EMAIL_RECEIVER**: The address where you want to receive alerts.

---

## 🚀 3. Manual Startup (Development)

### Start Backend
`python3 monitor.py`
The API will be available at http://127.0.0.1:8000.

### Start Frontend
1. `cd currency-ui`
2. `npm install`
3. `npm run dev`
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
