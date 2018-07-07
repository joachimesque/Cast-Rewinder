DEBUG = True # Set to False for production

APP_SECRET_KEY = 'a random string'

SQLALCHEMY_ECHO = True # Set to False for production
SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'
SQLALCHEMY_TRACK_MODIFICATIONS = True # Set to False for production

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = 'another random string'

WEBSITE_NAME = '⏮ Cast Rewinder'