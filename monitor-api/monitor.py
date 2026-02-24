import uvicorn
import httpx
import sqlite3
import logging
from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

# --- CONFIGURATION ---
API_KEY = "YOUR_TWELVE_DATA_API_KEY"  # <-- Replace with your real API key
SYMBOL = "EUR/CZK"
DATABASE_FILE = "forex_monitor.db"


# Setting up logging to track application behavior
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- DATABASE LOGIC ---
def init_db():
    """Initializes the SQLite database and creates the table if it doesn't exist."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS rates 
                        (timestamp TEXT, rate REAL, month TEXT)''')
        conn.commit()


def get_monthly_high(month_str):
    """Retrieves the highest exchange rate recorded in the given month."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(rate) FROM rates WHERE month = ?", (month_str,))
        result = cursor.fetchone()[0]
        return result if result else 0.0


# --- CORE MONITORING FUNCTION ---
def check_exchange_rate():
    """Fetches the current rate from Twelve Data and checks for a monthly high."""
    logger.info("Fetching exchange rate from Twelve Data...")
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={API_KEY}"

    try:
        with httpx.Client() as client:
            response = client.get(url)
            data = response.json()

            # Check for API-specific errors
            if "price" not in data:
                logger.error(f"API Error: {data.get('message', 'Unknown error occurred')}")
                return

            current_rate = float(data['price'])
            now = datetime.now()
            current_month = now.strftime("%Y-%m")

            # Check against the current record for this month
            highest_so_far = get_monthly_high(current_month)

            if highest_so_far > 0 and current_rate > highest_so_far:
                # This is where you would trigger a real notification (e.g., Telegram)
                print(f"\n🚀 NOTIFICATION: NEW MONTHLY HIGH! {current_rate} CZK is the highest rate this month!\n")
            elif highest_so_far == 0:
                logger.info("First entry for this month. Establishing baseline.")

            # Save the new data point to the database
            with sqlite3.connect(DATABASE_FILE) as conn:
                conn.execute("INSERT INTO rates VALUES (?, ?, ?)", 
                             (now.isoformat(), current_rate, current_month))
                conn.commit()

            logger.info(f"Current Rate: {current_rate} (Monthly High: {highest_so_far})")

    except Exception as e:
        logger.error(f"Unexpected error during rate check: {e}")


# --- FASTAPI SETUP & LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the startup and shutdown of the background scheduler."""
    # Startup actions
    init_db()
    scheduler = BackgroundScheduler()
    # Schedule task every 5 minutes (within Twelve Data free tier limits)
    scheduler.add_job(check_exchange_rate, 'interval', minutes=5)
    scheduler.start()
    logger.info("Background Scheduler started.")

    # Run an immediate check on startup
    check_exchange_rate()

    yield

    # Shutdown actions
    scheduler.shutdown()
    logger.info("Background Scheduler stopped.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In productie vervang je "*" door de URL van je website
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_status():
    """API endpoint to check the current monitor status via browser."""
    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT rate, timestamp FROM rates ORDER BY timestamp DESC LIMIT 1")
        last_entry = cursor.fetchone()

    if last_entry:
        current_month = datetime.now().strftime("%Y-%m")
        return {
            "status": "Online",
            "latest_rate": last_entry[0],
            "last_checked": last_entry[1],
            "monthly_high": get_monthly_high(current_month)
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
    print("Starting Currency Monitor on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
