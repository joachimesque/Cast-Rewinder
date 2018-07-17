from flask import Flask, g, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_babel import Babel, gettext

app = Flask(__name__, instance_relative_config=True)

app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
babel = Babel(app)

from . import views
from . import models

from flask_wtf.csrf import CSRFProtect

# For use with the POST API, we disable the global CSRF protection
# It is still enabled on Forms
# csrf = CSRFProtect(app)

app.secret_key = app.config['APP_SECRET_KEY']

# Babel & localization stuff
@babel.localeselector
def get_locale():
  browser = request.accept_languages.best_match(app.config['LANGUAGES'].keys())
  locale = session.get('lang', browser)
  return locale if locale in app.config['LANGUAGES'].keys() else 'en'


# Website footer info

import subprocess
import pickle
import time

@app.before_first_request
def before_first_request():
  # Get git ID, pickle it
  git_id = subprocess.check_output(["git", "rev-parse","HEAD"]).decode("ascii").strip()
  with open('pickle.pk', 'wb') as fi:
    pickle.dump(git_id, fi)

@app.before_request
def before_request():
  # set Locale
  if 'lang' in request.args:
    session['lang'] = request.args.get('lang', 'en')

  g.locale = get_locale()

  # Unpickle git ID from pickle.
  with open('pickle.pk', 'rb') as fi:
    g.git_id = pickle.load(fi)

  # Get request time
  g.request_start_time = time.time()
  g.request_time = lambda: "%.3fs" % (time.time() - g.request_start_time)
