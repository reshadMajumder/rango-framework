from rango import App

app = App()

# Import routes after app is created
from .routes import *

if __name__ == "__main__":
    app.run() 