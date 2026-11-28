import logging
import time
from app.db.database import SessionLocal
from app.services.notification_service import generate_reminders

def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            with SessionLocal() as db:
                generate_reminders(db)
        except Exception:
            logging.error("Reminder cycle failed; will retry")
        time.sleep(60)

if __name__ == "__main__":
    main()
