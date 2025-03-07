from rango import App
from .models import db  # Import db instance

app = App()
app.orm = db  # Set the app's ORM instance

# Import routes
from .routes import *

if __name__ == "__main__":
    app.run() 