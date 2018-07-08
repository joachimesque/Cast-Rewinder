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

It’s one of my first real *coding* projects. I’m a webdesigner who dabbles in Python, and I wanted to scratch an itch. I don’t know anything about software architecture and very little about databases. If you have suggestions for better, nicer, cleaner ways of doing things, please open an issue!

## Demo

[Demo on rewind.website](https://rewind.website)

## Installing

Install Python 3.7, pipy (the Python Package Manager) and PostgreSQL (the database) on your server.

    $ sudo apt-get install python3 pipy postgresql-10

Create a virtual environment like this:

    $ python -m venv .venv

Activate it with:

    $ source .venv/bin/activate

Install the requirements:

    (.venv) $ pip install -r requirements.txt

Create the user (if needed) and database:

    (.venv) $ createdb castrewinder   

Copy `config.py` to `./instances/config.py`, and edit your preferences (using Nano, Ctrl-X saves, and Ctrl-C exits the editor). `APP_SECRET_KEY` and `WTF_CSRF_SECRET_KEY` must be randomly generated strings.

    (.venv) $ cp config.py ./instances/config.py
    (.venv) $ nano ./instances/config.py

Then run the install script:

    (.venv) $ python setup.py

## Running

### Development

When developing, run it via the run script:

    (.venv) $ python run.py

### Production

I don’t know how that works yet.


## Copyrights and License

Unless otherwise specified, this code is copyright 2018 Joachim Robert and released under the GNU Affero General Public License v3.0. Learn more about this license : https://choosealicense.com/licenses/agpl-3.0/

This work uses code from:

- [Bulma](https://bulma.io), which is copyright 2018 Jeremy Thomas and whose code is released under [the MIT license](https://github.com/jgthms/bulma/blob/master/LICENSE).
- [clipboard.js](https://clipboardjs.com), which is copyright Zeno Rocha, and whose code is released under [the MIT License](http://zenorocha.mit-license.org/)
