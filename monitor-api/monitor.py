import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import uvicorn
import httpx
import sqlite3
import logging
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from os import getenv

# Load the .env file to access environment variables
load_dotenv()

# --- CONFIGURATION ---
api_key = os.getenv("MONITOR_API_KEY")
if not api_key:
    raise ValueError("MONITOR_API_KEY not found in .env file. Is there any .env file created?")
telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
email_user = os.getenv("EMAIL_USER")
email_password = os.getenv("EMAIL_PASSWORD")
smtp_server = os.getenv("SMTP_SERVER")
smtp_port = int(os.getenv("SMTP_PORT"))
email_receiver = os.getenv("EMAIL_RECEIVER")
symbol = os.getenv("SYMBOL")  # e.g. "EUR/USD"
# Get the base and quote currency from the symbol (e.g. "EUR/USD" -> base: "EUR", quote: "USD")
quote = symbol.split('/')[1]
lookback_days = int(os.getenv("LOOKBACK_DAYS", 45))  # Default to 45 days if not specified
api_port = int(os.getenv("API_PORT"))  # e.g. 8000
debug_mode = os.getenv("DEBUG", "False").lower() == "true"
if debug_mode:
    print("⚠️ DEBUG MODE ENABLED")
log_level = logging.DEBUG if debug_mode else logging.WARNING
# log_level = logging.DEBUG if debug_mode else logging.INFO

DATABASE_FILE = "forex_monitor.db"


# Setting up logging to track application behavior
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# --- NOTIFICATIONS ---
def send_telegram_msg(message):
    """Sends a message to a Telegram bot."""
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    try:
        with httpx.Client() as client:
            client.post(url, json={"chat_id": telegram_chat_id, "text": message})
            logger.info("Telegram notification sent.")
    except Exception as e:
        logger.error(f"Telegram failed: {e}")

def send_email_alert(subject, body):
    """Sends an email alert using SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = email_user
    msg['To'] = email_receiver

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_user, email_password)
            server.send_message(msg)
            logger.info("Email notification sent.")
    except Exception as e:
        logger.error(f"Email failed: {e}")

# --- DATABASE LOGIC ---
def init_db():
    """Initializes the SQLite database and creates the table if it doesn't exist."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rate REAL NOT NULL
            )
        """)
        conn.commit()


def cleanup_old_data():
    """Verwijdert data die ouder is dan LOOKBACK_DAYS + een marge van 5 dagen."""
    # We houden iets meer data aan dan strikt nodig (marge van 5 dagen) voor de zekerheid
    retention_days = LOOKBACK_DAYS + 5
    cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
    
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rates WHERE timestamp < ?", (cutoff_date,))
            deleted_rows = cursor.rowcount
            if deleted_rows > 0:
                logger.info(f"Cleanup: {deleted_rows} oude records verwijderd.")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")


def get_high_lookback_period():
    """Retrieves the highest exchange rate recorded in the last 45 days."""
    # Calculate the date X days ago
    cutoff_date = (datetime.now() - timedelta(days=lookback_days)).isoformat()
    
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        #  select the MAX rate where the timestamp is newer than our cutoff
        cursor.execute("SELECT MAX(rate) FROM rates WHERE timestamp > ?", (cutoff_date,))
        result = cursor.fetchone()[0]
        return result if result else 0.0


def get_effective_period():
    """Calculates the effective period based on the amount of data collected so far."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # Get the earliest timestamp in the table
        cursor.execute("SELECT timestamp FROM rates ORDER BY timestamp ASC LIMIT 1")
        first_entry = cursor.fetchone()
        
    if not first_entry:
        return 0
        
    first_date = datetime.fromisoformat(first_entry[0])
    days_since_start = (datetime.now() - first_date).days
    
    # We return the smallest value: either the 45 days,
    # or the number of days since the start
    return min(lookback_days, max(1, days_since_start))

# --- CORE MONITORING FUNCTION ---
def check_exchange_rate():
    """Fetches the current rate from Twelve Data and checks for a monthly high."""
    logger.info("Fetching exchange rate from Twelve Data...")
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"

    try:
        with httpx.Client() as client:
            response = client.get(url)
            data = response.json()
            current_rate = float(data['price'])

        highest_so_far = get_high_lookback_period()

        if highest_so_far > 0 and current_rate > highest_so_far:
            # Trigger alert if new high is reached
            effective_nr_of_days = get_effective_period()

            msg = f"🚀 {symbol} Alert: Highest rate in the last {effective_nr_of_days} days!\nCurrent rate: {current_rate} {quote}\nPrevious high: {highest_so_far} {quote}"
            if debug_mode: 
                print(msg)
            
            # Send notifications
            send_telegram_msg(msg)
            email_subject = f"Currency Alert: New {effective_nr_of_days}-Day Record"
            send_email_alert(email_subject, msg)
            
            if debug_mode: 
                print(f"\n🚀 NOTIFICATION SENT: {current_rate} {quote}\n")

        elif highest_so_far == 0:
            logger.info("First entry for this month. Establishing baseline.")

        # Save the new data point to the database
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.execute("INSERT INTO rates (timestamp, rate) VALUES (?, ?)", 
                         (datetime.now().isoformat(), current_rate))
            conn.commit()

        logger.info(f"Current Rate: {current_rate} (Monthly High: {highest_so_far})")

    except Exception as e:
        logger.error(f"Unexpected error during rate check: {e}")

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    init_db()
    scheduler = BackgroundScheduler()

    # Task 1: Schedule task every 5 minutes (within Twelve Data free tier limits)
    scheduler.add_job(check_exchange_rate, 'interval', minutes=5)

    # Task 2: Daily cleanup at 3 AM
    scheduler.add_job(cleanup_old_data, 'cron', hour=3, minute=0)
    scheduler.start()
    logger.debug("Lifespan: Scheduler started.")
    
    check_exchange_rate()

    yield # Here runs the FastAPI application
    
    # Shutdown logic
    scheduler.shutdown()
    logger.debug("Lifespan: Scheduler shut down.")

# --- API ENDPOINTS ---
app = FastAPI(debug=debug_mode, lifespan=lifespan)

# Allow all origins for CORS (for development purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change the '*' in production for your website url
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API ENDPOINTS ---
@app.get("/")
def read_status():
    """API endpoint to check the current monitor status via browser."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT rate, timestamp FROM rates ORDER BY timestamp DESC LIMIT 1")
        last_entry = cursor.fetchone()

    if last_entry:
        return {
            "status": "Online",
            "latest_rate": last_entry[0],
            "last_checked": last_entry[1],
            "high_period": get_high_lookback_period(),
            "effective_days": get_effective_period()
        }
    return {"status": "Waiting for initial data..."}


@app.get("/history")
def get_history():
    """Returns the last 100 data points for the chart."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        # Get last 100 entries, then reverse them to have chronological order
        cursor.execute("SELECT rate, timestamp FROM rates ORDER BY timestamp DESC LIMIT 100")
        rows = cursor.fetchall()
        
    history = [{"rate": row[0], "time": row[1].split('T')[1][:5]} for row in reversed(rows)]
    return history


# --- APPLICATION ENTRY POINT ---
if __name__ == "__main__":
    # Starting the web server locally on port 8000
    print("Starting Currency Monitor on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=api_port, log_level=logging.WARNING)
