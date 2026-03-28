import time
import os
import shutil
import pandas as pd
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from app.db.ops_helpers import record_sale_op
from app.db.sync import sync_to_csv
from app.services.stock_engine import stock_engine

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WATCH_DIR = "data/sync/incoming"
ARCHIVE_DIR = "data/sync/archive"

class SalesSyncHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.csv'):
            logger.info(f"New sales file detected: {event.src_path}")
            # Wait a moment to ensure file is fully written
            time.sleep(1)
            self.process_file(event.src_path)

    def process_file(self, file_path):
        try:
            df = pd.read_csv(file_path)
            required_cols = ['item', 'quantity', 'revenue']
            if not all(col in df.columns for col in required_cols):
                logger.error(f"Invalid CSV format in {file_path}. Missing columns: {required_cols}")
                return

            success_count = 0
            for index, row in df.iterrows():
                item = str(row['item'])
                qty = int(row['quantity'])
                rev = float(row['revenue'])
                
                # 1. Record in DB (Sales + Inventory menu stock)
                if record_sale_op(item, qty, rev):
                    # 2. Deduct from Ingredient/Grocery Stock
                    try:
                        stock_engine.deduct_sale(item, qty)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to deduct ingredients for {item}: {e}")
                else:
                    logger.warning(f"Failed to record sale for {item} from {file_path}")

            # 3. Sync DB back to CSV (for the main data/ folder)
            sync_to_csv()
            logger.info(f"Successfully processed {success_count} sales from {file_path}")

            # 4. Archive file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.basename(file_path)
            archive_path = os.path.join(ARCHIVE_DIR, f"{timestamp}_{filename}")
            shutil.move(file_path, archive_path)
            logger.info(f"Moved {file_path} to {archive_path}")

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

def main():
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    event_handler = SalesSyncHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    logger.info(f"Sync Watcher started. Monitoring {WATCH_DIR}...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
