DEBUG = True # Turns on debugging features in Flask

APP_SECRET_KEY = 'a random string'

SQLALCHEMY_ECHO = True
SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'
SQLALCHEMY_TRACK_MODIFICATIONS = True

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = 'another random string'
