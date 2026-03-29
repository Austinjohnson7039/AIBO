from sqlalchemy import text
from app.db.database import engine
from app.db.models import Base

def migrate():
    # 1. Create new tables (Vendor, PurchaseOrder)
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add vendor_id to ingredients
    with engine.begin() as conn:
        try:
            # If Postgres, the syntax is valid. If SQLite, simple ADD COLUMN works although without the FK constraint perfectly applied, but sufficient for ORM.
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN vendor_id INTEGER;"))
            print("Successfully added vendor_id column to ingredients.")
        except Exception as e:
            print("Notice: vendor_id already exists or error occurred: ", str(e))

if __name__ == "__main__":
    migrate()
