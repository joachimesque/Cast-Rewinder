from . import app
from flask import render_template
from flask import request
from flask import abort
from flask import flash
import json
from urllib.parse import urlparse

import feed_worker
from .utils import get_frequency, parse_frequency, generate_url, build_feed, get_options, parse_options

from .forms import UrlForm

from . import db
from .models import Feed, Episode

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.route('/', methods=["GET", "POST"])
def index():
  form = UrlForm()
  if form.validate_on_submit():
    u = urlparse(url = request.form['url'])
    
    if u.scheme + '://' + u.netloc + '/' == request.host_url:
      # If the supplied URL is the same as the app’s URL
      # Don’t throw bricks into the machine, kids.
      # Perhaps there should be a protection against URL-shorteners, too.
      flash("🤔 DUDE. NOT FUNNY.")
    else:
      # TODO : get a queue going for these kinds of jobs
      valid_feed = feed_worker.import_feed(request.form['url'])
      
      if not valid_feed:
        flash("Invalid URL.")

      else:

        frequency = get_frequency(request_form = request.form)
        options = get_options(request_form = request.form)

        feed_url = request.form['url']
        if u.netloc == 'itunes.apple.com':
          feed_url = feed_worker.get_feed_from_itunes_api(itunes_url = feed_url)

        feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

        end_url = request.url + generate_url(feed_id = feed_object.id, frequency = frequency, options = options)

        return render_template('index.html', form = form, end_url = end_url, feed_object = json.loads(feed_object.content))

  return render_template('index.html', form = form)


@app.route('/<feed_id>/<frequency>/<start_date>', defaults = {'options': ''})
@app.route('/<feed_id>/<frequency>/<start_date>/<options>')
def serve_feed(feed_id, frequency, start_date, options):

  publication_dates = parse_frequency(frequency = frequency, start_date = start_date)

  feed_object = db.session.query(Feed).filter(Feed.id == feed_id).one()

  options = parse_options(options = options)

  feed_format = options['format'] if 'format' in options else 'feed_rss'

  order = Episode.published.asc() 
  if 'order' in options:
    if options['order'] == 'desc':
      order = Episode.published.desc()
  
  if 'start_at' in options:

    start_at = int(options['start_at']) - 1

    feed_entries = db.session.query(Episode).\
                       filter(Episode.feed_id == feed_id).\
                       order_by(order).\
                       offset(start_at).\
                       limit(publication_dates['limit']).\
                       all()

  else:
    feed_entries = db.session.query(Episode).\
                       filter(Episode.feed_id == feed_id).\
                       order_by(order).\
                       limit(publication_dates['limit']).\
                       all()


  feed = build_feed(feed_object = feed_object, feed_entries = feed_entries, publication_dates = publication_dates, feed_format = feed_format)

  return feed

@app.route('/about')
def about():
  return render_template('about.html')

