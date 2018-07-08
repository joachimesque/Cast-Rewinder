from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)

app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)

from . import views
from . import models

from flask_wtf.csrf import CSRFProtect

# For use with the POST API, we disable the global CSRF protection
# It is still enabled on Forms
# csrf = CSRFProtect(app)

app.secret_key = app.config['APP_SECRET_KEY']
