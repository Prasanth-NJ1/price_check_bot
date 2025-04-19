from apscheduler.schedulers.background import BackgroundScheduler
import logging
from price_checker import check_all_prices
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='scheduler.log'
)
logger = logging.getLogger('scheduler')

def start_scheduler():
    """Start the scheduler for price checking."""
    scheduler = BackgroundScheduler()
    
    # Check prices every 6 hours
    scheduler.add_job(check_all_prices, 'interval', hours=6, id='price_check')
    
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started. Price check will run every 6 hours.")
    return scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()
    
    try:
        # Keep the script running
        print("Scheduler is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler shut down.")