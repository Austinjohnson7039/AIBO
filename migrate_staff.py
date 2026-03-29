from app.db.database import engine
from app.db.models import Base

# This will create tables that don't exist yet but won't touch existing ones
Base.metadata.create_all(bind=engine)
print("Staff and Wastage Tables verified!")
