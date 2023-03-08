from flask_sqlalchemy import SQLAlchemy
from flask import Flask

# Create a global variable for the db object
db = SQLAlchemy()


# Define a function to initialize the db object with the Flask app
def init_db(app: Flask) -> None:
    db.init_app(app)
