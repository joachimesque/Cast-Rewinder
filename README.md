# ⏮ Cast Rewinder

Subscribe to podcasts from the start!

## Installing

Install Python 3.7, pipy (the Python Package Manager) and PostgreSQL (the database) on your server.

    $ sudo apt-get install python3 pipy

Create a virtual environment like this:

    $ python -m venv .venv

Activate it with:

    $ source .venv/bin/activate

Install the requirements:

    (.venv) $ pip install -r requirements.txt

Create the user and database:

    (.venv) $ createdb castrewinder   

Then run the install script:

    (.venv) $ python setup.py

## Running

  When developing, run it via the run script:

    (.venv) $ python run.py
