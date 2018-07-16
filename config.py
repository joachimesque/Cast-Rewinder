DEBUG = True # Set to False for production

APP_SECRET_KEY = 'a random string'

SQLALCHEMY_ECHO = True # Set to False for production
SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'
SQLALCHEMY_TRACK_MODIFICATIONS = True # Set to False for production

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = 'another random string'

BABEL_DEFAULT_LOCALE = 'en'
BABEL_TRANSLATION_DIRECTORIES = '../translations'
LANGUAGES = {
    'en': 'English',
    'fr': 'Français'
}

WEBSITE_NAME = '⏮ Cast Rewinder'