"""
DB Migration script
Usage:
python manage.py db migrate - creates migration script
python manage.py db upgrade - upgrades database with migration script

https://flask-migrate.readthedocs.io/en/latest/
"""

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from os import environ

from flowapp import app, db
import config


# Configurations
try:
    env = environ['USERNAME']
except KeyError as e:
    env = 'Production'

if env == 'albert':
    print("DEVEL")
    app.config.from_object(config.DevelopmentConfig)
else:
    print("PRODUCTION")
    app.config.from_object(config.ProductionConfig)

migrate = Migrate(app, db, compare_type=True)

manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()