from flask.cli import FlaskGroup
from main import app, db

cli = FlaskGroup(app)


@cli.command("create_db")
def create_db():
    db.create_all()
    print("Database created")


if __name__ == "__main__":
    cli()
    create_db()
