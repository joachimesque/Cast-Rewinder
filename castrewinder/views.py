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

@app.errorhandler(500)
def error(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 500

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
        flash("The supplied URL is not a podcast feed.")

      else:

        frequency = get_frequency(request_form = request.form)
        options = get_options(request_form = request.form)

        if frequency == '':
          flash('You did not select week days, please do now or select another frequency.')

        else:

          feed_url = request.form['url']
          if u.netloc == 'itunes.apple.com':
            feed_url = feed_worker.get_feed_from_itunes_api(itunes_url = feed_url)

          feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

          end_url = request.host_url + generate_url(feed_id = feed_object.id,
                                                    frequency = frequency,
                                                    options = options)

          return render_template('index.html', form = form, end_url = end_url, feed_object = json.loads(feed_object.content))

  return render_template('index.html', form = form)


@app.route('/<feed_id>/<frequency>/<start_date>', defaults = {'options': ''})
@app.route('/<feed_id>/<frequency>/<start_date>/<options>')
def serve_feed(feed_id, frequency, start_date, options):

  publication_dates = parse_frequency(frequency = frequency, start_date = start_date)

  if not publication_dates:
    abort(500)


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


@app.route('/api/')
def about_api():
  return render_template('api.html')

@app.route('/api/get', methods=["GET"])
@app.route('/api/post', methods=["POST"])
def api():
  response = {}
  the_request = {}

  if request.method == 'GET':
    for key, value in request.args.items():
      the_request[key] = value
  elif request.method == 'POST':
    for key, value in request.get_json(force=True).items():
      the_request[key] = value

  if 'url' in the_request:
    url = the_request['url']
    u = urlparse(url = url)

    if u.scheme + '://' + u.netloc + '/' == request.host_url:
      # If the supplied URL is the same as the app’s URL
      # Don’t throw bricks into the machine, kids.
      # Perhaps there should be a protection against URL-shorteners, too.
      response['error'] = 'u kno what u did'

    else:
      # TODO : get a queue going for these kinds of jobs
      valid_feed = feed_worker.import_feed(url)
      
      if not valid_feed:
        response['error'] = 'The supplied URL is not a podcast feed.'
        
      else:

        if 'frequency' not in the_request:
          the_request['frequency'] = 'weekly'
          response['warning'] = {
            'type': 'light warning',
            'content': 'No frequency was supplied, going with the default (weekly)'}


        frequency = get_frequency(request_form = the_request)
        options = get_options(request_form = the_request)

        if frequency == '':
          frequency = 'weekly'
          response['warning'] = {
            'type': 'stern warning',
            'content': 'No custom day was supplied despite `custom days` frequency, going with the default frequency (weekly)'}

        feed_url = url
        if u.netloc == 'itunes.apple.com':
          feed_url = feed_worker.get_feed_from_itunes_api(itunes_url = feed_url)

        feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

        end_url = request.host_url + generate_url(feed_id = feed_object.id, frequency = frequency, options = options)


        response['feed_id'] = feed_object.id
        response['url'] = end_url

  else:
    response['error'] = 'No URL provided'
        

  return json.dumps(response)
