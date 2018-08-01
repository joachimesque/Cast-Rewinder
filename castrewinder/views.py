from . import app
from flask import render_template, request, abort, flash, Response, g
import werkzeug
from flask_babel import Babel, gettext
import json
import hashlib
import datetime
from urllib.parse import urlparse

import feed_worker
from .utils import get_frequency, parse_frequency, generate_url, build_xml_feed, build_json_feed, get_options, parse_options

from .forms import UrlForm

from . import db
from .models import Feed, Episode

# HTTP Exception : 304 Not Modified (empty response)
class NotModified(werkzeug.exceptions.HTTPException):
    code = 304
    def get_response(self, environment):
        return Response(status=304)

# HTTP Error : 404 Not Found
@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.'+ g.locale +'.html'), 404

# HTTP Error : 500 Internal Server Error
@app.errorhandler(500)
def error(e):
    # note that we set the 500 status explicitly
    return render_template('500.'+ g.locale +'.html'), 500

@app.route('/', methods=["GET", "POST"])
def index():
  form = UrlForm()
  if form.validate_on_submit():

    frequency = get_frequency(request_form = request.form)
    options = get_options(request_form = request.form)

    if frequency == '':
      flash(gettext('You did not select week days, please do now or select another frequency.'))
      return render_template('index.html', form = form)


    u = urlparse(url = request.form['url'])
    
    if u.scheme + '://' + u.netloc + '/' == request.host_url:
      # If the supplied URL is the same as the app’s URL
      # Don’t throw bricks into the machine, kids.
      # Perhaps there should be a protection against URL-shorteners, too.
      flash(gettext("🤔 DUDE. NOT FUNNY."))
      return render_template('index.html', form = form)
    else:
      end_url = generate_url(feed_id = 0,
                              frequency = frequency,
                              options = options)
      request_object = {'url': request.form['url'], 'end_url': end_url[1:]}
      return render_template('index.html', form = form, request_json = request_object)

  return render_template('index.html', form = form)



@app.route('/ajax/geturl', methods=["PUT"])
def ajax_geturl():

  request_data = json.loads(request.get_data())

  u = urlparse(url = request_data['url'])
  
  feed_url = feed_worker.check_url(url = request_data['url'])

  # TODO : get a queue going for these kinds of jobs
  valid_feed = feed_worker.import_feed(feed_url)
  
  if not valid_feed:
    if u.netloc.endswith('soundcloud.com'):
      error = gettext("This SoundCloud user does not have a podcast feed. Ask them to set one up!")
    else:
      error = gettext("The supplied URL is not a podcast feed. Unsure why you got this answer, thinking it might be a bug? Send me an email.")

    response = str(json.dumps({'error': error}))
  else:

    feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

    return_object = {'feed_id': feed_object.id, 'content': json.loads(feed_object.content)} 

    response = str(json.dumps(return_object))

  r = Response(response=response, status=200, mimetype="application/json")
  r.headers["Content-Type"] = "application/json; charset=utf-8"

  return r



@app.route('/<feed_id>/<frequency>/<start_date>', defaults = {'options': ''})
@app.route('/<feed_id>/<frequency>/<start_date>/<options>')
def serve_feed(feed_id, frequency, start_date, options):
  # check if feed_id is an int, if not abort with 404
  try:
    feed_id = int(feed_id)
  except ValueError:
    abort(404)

  publication_dates = parse_frequency(frequency = frequency, start_date = start_date)
  
  # generation of Last Modified and ETag
  if publication_dates['limit'] == 0:
    last_modified = datetime.datetime.strftime(datetime.datetime.now(), '%a, %d %b %Y %H:%M:%S GMT')
    etag = '"%s"' % hashlib.sha1(str(datetime.datetime.now()).encode('utf-8')).hexdigest()
  else:
    last_modified = datetime.datetime.strftime(publication_dates['dates'][-1], '%a, %d %b %Y %H:%M:%S GMT')
    etag = '"%s"' % hashlib.sha1(str(publication_dates['dates'][-1]).encode('utf-8')).hexdigest()

  # if Request headers match Last Modified and Etag, raise a 304 response
  if request.headers.get('If-Modified-Since') == last_modified \
    or request.headers.get('If-None-Match') == etag:
    raise NotModified

  # get the list of all feeds IDs
  feeds_ids = [f[0] for f in db.session.query(Feed.id).all()]
  # check if feed_id is valid, if not abort with 404
  if feed_id not in feeds_ids:
    abort(404)


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



  if feed_format == 'feed_json':
    feed = build_json_feed(feed_object = feed_object, feed_entries = feed_entries, publication_dates = publication_dates, options = options)
    r = Response(response=feed, status=200, mimetype="application/json")
    r.headers["Content-Type"] = "application/json; charset=utf-8"
    
  else:
    feed = build_xml_feed(feed_object = feed_object, feed_entries = feed_entries, publication_dates = publication_dates, options = options, feed_format = feed_format)
    r = Response(response=feed, status=200, mimetype="text/xml")
    r.headers["Content-Type"] = "text/xml; charset=utf-8"

  # Add Last-Modified and ETag headers
  r.headers["Last-Modified"] = last_modified
  r.headers["ETag"] = etag

  return r

@app.route('/about/')
def about():
  return render_template('about.'+ g.locale +'.html')


@app.route('/api/')
def about_api():
  return render_template('api.'+ g.locale +'.html')

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

      feed_url = feed_worker.check_url(url = url)

      # TODO : get a queue going for these kinds of jobs
      valid_feed = feed_worker.import_feed(feed_url)
      
      if not valid_feed:
        if u.netloc.endswith('soundcloud.com'):
          response['error'] = 'This SoundCloud user does not have a podcast feed. Ask them to set one up!'
        else:
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

        feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

        end_url = request.host_url + generate_url(feed_id = feed_object.id, frequency = frequency, options = options)


        response['feed_id'] = feed_object.id
        response['url'] = end_url

  else:
    response['error'] = 'No URL provided'

  r = Response(response=json.dumps(response), status=200, mimetype="application/json")
  r.headers["Content-Type"] = "application/json; charset=utf-8"

  return r
