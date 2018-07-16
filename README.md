# ⏮ Cast Rewinder

![](https://img.shields.io/badge/please-help-yellow.svg)
![](https://img.shields.io/badge/trapped_in-SVG_factory-red.svg)
![](https://img.shields.io/badge/running_out-of_XML-yellow.svg)
![](https://img.shields.io/badge/send-tags-orange.svg)

Subscribe to podcasts from the beginning!

## What’s the deal?

**Cast Rewinder allows you to subscribe to a podcast from the beginning.**

Every so often I discover a podcast that sounds really great, but it has started publishing episodes for so long that it’s a chore to go back at the beginning.

Now with Cast Rewinder you can subscribe to that podcast and get updates, starting from the beginning. You can set the frequency (monthly, weekly, daily… and even on specified days of the week) and other options, like the feed format or at which episode in the feed to start your discovery.

Cast Rewinder runs [rewind.website](https://rewind.website).

The idea originates from Brendan Hutchins in the podcast [Bitrate](http://bitratepod.com/), in [June 29th, 2018 episode](http://bitratepod.com/e/365db62d09d690/). Thanks for the inspiration!

It’s one of my first real *coding* projects. I’m a webdesigner who dabbles in Python, and I wanted to scratch an itch. I don’t know anything about software architecture and very little about databases. If you have suggestions for better, nicer, cleaner ways of doing things, please open an issue!

## Demo

[Demo on rewind.website](https://rewind.website)

## Installing

Install Python 3.7, pypi (the Python Package Manager) and PostgreSQL (the database) on your server.

    $ sudo apt-get install python3 pypi postgresql

Create a virtual environment like this:

    $ python -m venv .venv

Activate it with:

    $ source .venv/bin/activate

Install the requirements:

    (.venv) $ pip install -r requirements.txt

Create the user (if needed) and database:

    (.venv) $ createdb castrewinder   

Copy `config.py` to `./instances/config.py`, and edit your preferences (using Nano, Ctrl-O saves, and Ctrl-X exits the editor). `APP_SECRET_KEY` and `WTF_CSRF_SECRET_KEY` must be randomly generated strings.

    (.venv) $ cp config.py ./instances/config.py
    (.venv) $ nano ./instances/config.py

Then run the install script:

    (.venv) $ python setup.py

## Running

### Development

When developing, run it via the run script:

    (.venv) $ python run.py

### Production

What you really want is to read this doc : <http://flask.pocoo.org/docs/1.0/deploying/>

On [rewind.website](https://rewind.website/) I used [uWSGI](http://flask.pocoo.org/docs/1.0/deploying/uwsgi/) and nginx, on an Ubuntu machine, and it seems to be working.

### Migrations

If you read this, let’s hope you know what you do. Anyways, migrations are taken care of by Alembic.

First, configure your Alembic `alembic.ini` by changing the value of `sqlalchemy.url`. Then you can:

    (.venv) $ alembic upgrade head

#### Cron job

Here is the line for the Cron job that’ll update the feeds every day at 3 in the morning (server time).

    0 3 * * * cd ~/Cast-Rewinder/ ; . ~/Cast-Rewinder/.venv/bin/activate ; ~/Cast-Rewinder/.venv/bin/python ~/Cast-Rewinder/feed_worker.py -u

You could use a different update frequency setting. As this app is geared mostly towards old / defunct podcasts with big back catalogs, I don’t know if there’s a need for hourly updates. Anyways, if you need other options, check [crontab.guru](https://crontab.guru/#0/15_*_*_*_*)

## Copyrights and License

Unless otherwise specified, this code is copyright 2018 Joachim Robert and released under the GNU Affero General Public License v3.0. Learn more about this license : https://choosealicense.com/licenses/agpl-3.0/

This work uses code from:

- [Bulma](https://bulma.io), which is copyright 2018 Jeremy Thomas and whose code is released under [the MIT license](https://github.com/jgthms/bulma/blob/master/LICENSE).
- [clipboard.js](https://clipboardjs.com), which is copyright Zeno Rocha, and whose code is released under [the MIT License](http://zenorocha.mit-license.org/)
- [jsTimezoneDetect](https://bitbucket.org/pellepim/jstimezonedetect) is freely distributable under the terms of the [MIT license](https://github.com/moment/moment/blob/develop/LICENSE).
