from os import environ

from flowapp import app, db
import config

# Configurations
try:
    env = environ['EXAFS_ENV']
except KeyError as e:
    env = 'Production'

if env == 'devel':
    app.config.from_object(config.DevelopmentConfig)
    app.config.update(
        DEVEL=True
    )
else:
    app.config.from_object(config.ProductionConfig)
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        DEVEL=False
    )

# init database object
db.init_app(app)

# run app
if __name__ == '__main__':
    app.run(host='::', port=8080, debug=True)
