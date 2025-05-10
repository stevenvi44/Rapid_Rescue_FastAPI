from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from urllib.parse import quote_plus

# Database configuration
server = 'DESKTOP-N99NNCP'
database = 'Rapid_Rescue'
driver = 'ODBC Driver 17 for SQL Server'

# Connection string
DATABASE_URL = f"mssql+pyodbc://@{server}/{database}?driver={quote_plus(driver)}&trusted_connection=yes"

engine = create_engine(DATABASE_URL)

# provides a connection to interact with the database and perform queries, inserts, updates, and deletions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# define ORM models, create base for all models, and provide access to metadata
class Base(DeclarativeBase):
    pass

# Database instance for async operations
metadata = MetaData()

# Dependency function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
