from rango import ORM

# Initialize the ORM
db = ORM()

# Define your models here
def init_db():
    """Initialize database tables"""
    db.create_table("users", {
        "id": "INTEGER PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "email": "TEXT UNIQUE NOT NULL"
    })

    db.create_table("products", {
        "id": "INTEGER PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "price": "REAL NOT NULL",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    })

if __name__ == "__main__":
    init_db() 