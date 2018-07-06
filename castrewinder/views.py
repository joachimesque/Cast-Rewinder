from . import app
from flask import render_template
from flask import request
import datetime
import json
from urllib.parse import urlparse

from feedgen.feed import FeedGenerator
from dateutil import relativedelta

import feed_importer

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
    
    if u.scheme + '://' + u.netloc + '/' != request.url:
      # TODO : get a queue going for these kinds of works
      feed_importer.import_feed(request.form['url'])
      
      frequency = get_frequency(request_form = request.form)


      feed_url = request.form['url']
      if u.netloc == 'itunes.apple.com':
        feed_url = feed_importer.get_feed_from_itunes_api(itunes_url = feed_url)

      feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

      end_url = request.url + generate_url(feed_id = feed_object.id, frequency = frequency)

      return render_template('index.html', form = form, end_url = end_url, feed_object = json.loads(feed_object.content))

  return render_template('index.html', form = form)


@app.route('/<feed_id>/<frequency>/<start_date>', defaults = {'options': ''})
@app.route('/<feed_id>/<frequency>/<start_date>/<options>')
def serve_feed(feed_id, frequency, start_date, options):

  publication_dates = parse_frequency(frequency = frequency, start_date = start_date)
  #return "/%s/%s/%s/%s" % (feed_id, frequency, start_date, options)
  feed_object = db.session.query(Feed).filter(Feed.id == feed_id).one()
  feed_entries = db.session.query(Episode).\
                     filter(Episode.feed_id == feed_id).\
                     order_by(Episode.published).\
                     limit(publication_dates['limit']).\
                     all()

  feed = build_feed(feed_object = feed_object, feed_entries = feed_entries, publication_dates = publication_dates)

  return feed


def get_frequency(request_form):

  if request_form['frequency'] in ['daily', 'weekly', 'monthly']:
    frequency = request_form['frequency']
  elif request_form['frequency'] == 'weekdays':
    weekdays_frequency = []
    for form_element in request_form:
      if form_element[:-3] == 'weekday_':
        weekdays_frequency.append(form_element[-3:])

    frequency = '-'.join(weekdays_frequency)

  return frequency

def parse_frequency(frequency, start_date):
  dates = []

  if len(str(start_date)) == 8:
    tz = '+0000'
    start_date = str(start_date) + tz
  else:
    tz = start_date[9:]
  start_datetime = datetime.datetime.strptime(str(start_date), '%Y%m%d%z')

  now = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)

  delta = now - start_datetime
  monthdelta = relativedelta.relativedelta(now, start_datetime)

  if frequency == 'daily':
    # I add 1 to delta.days so it'll take today into account
    limit = delta.days + 1
    for day in range(limit):
      day_date = start_datetime + relativedelta.relativedelta(days=+day)
      dates.append(day_date)
  elif frequency == 'weekly':
    for day in range(0, delta.days + 1, 7):
      day_date = start_datetime + relativedelta.relativedelta(days=+day)
      dates.append(day_date)
    limit = len(dates)
  elif frequency == 'monthly':
    # I add 1 to monthdelta.months so it'll take today into account
    limit = monthdelta.months + 1
    for day in range(limit):
      day_date = start_datetime + relativedelta.relativedelta(months=+day)
      dates.append(day_date)
  else:
    # if we get something like 'mon-wed-fri'
    # we start by checking if weekdays exist
    possible_weekdays = ['mon','tue','wed','thu','fri','sat','sun']
    weekdays_list = [possible_weekdays.index(x) + 1 for x in frequency.split('-') if x in possible_weekdays]

    for day in range(delta.days + 1):
      # I add 1 to delta.days so it'll take today into account
      day_date = start_datetime + relativedelta.relativedelta(days=+day)
      if day_date.isoweekday() in weekdays_list:
        dates.append(day_date)

    limit = len(dates)

  return {'dates': dates, 'limit': limit}



def generate_url(feed_id, frequency):
  start_date = datetime.datetime.now().strftime('%Y%m%d')
  return "%s/%s/%s" % (feed_id, frequency, start_date)

def build_feed(feed_object, feed_entries, publication_dates):
  feed = json.loads(feed_object.content)

  fg = FeedGenerator()

  fg.load_extension('podcast')

  fg.id(request.url)
  fg.title(feed['title'] if 'title' in feed else '')
  fg.subtitle(feed['subtitle'] if 'subtitle' in feed else '')

  fg.link(href = feed['link'] if 'link' in feed else '', rel = 'self')
  for link in feed['links']:
    fg.link(rel  = link['rel']  if 'rel'  in link else '',
            type = link['type'] if 'type' in link else '',
            href = link['href'] if 'href' in link else '')

  if 'author_detail' in feed:
    fg.author(name  = feed['author_detail']['name']  if 'name'  in feed['author_detail'] else '',
              email = feed['author_detail']['email'] if 'email' in feed['author_detail'] else '')
  for author in feed['authors']:
    fg.author(name  = author['name']  if 'name'  in author else '',
              email = author['email'] if 'email' in author else '')

  fg.logo(feed['image']['href'])
  fg.language(feed['language'] if 'language' in feed else '')
  fg.rights(feed['rights'] if 'rights' in feed else '')
  fg.generator('Cast Rewinder & python-feedgen')

  if feed['itunes_explicit']:
    explicit = 'yes'
  else:
    explicit = 'no'
  fg.podcast.itunes_explicit(explicit)
  fg.podcast.itunes_new_feed_url(feed['itunes_new-feed-url'] if 'itunes_new-feed-url' in feed else '')
  fg.podcast.itunes_summary(feed['summary'] if 'summary' in feed else '')
  
  fg.description(feed['summary'] if 'summary' in feed
            else feed['description'] if 'description' in feed
            else feed['subtitle'] if 'subtitle' in feed
            else 'This feed was generated by Cast Rewinder')
  # fg.podcast.itunes_type(feed['itunes_type'])

  for index, entry in enumerate(feed_entries):
    episode = json.loads(entry.content)

    fe = fg.add_entry()
    fe.id(episode['id'] if 'id' in episode else '')
    fe.title(episode['title'] if 'title' in episode else '')
    fe.podcast.itunes_subtitle(episode['subtitle'] if 'subtitle' in episode else '')
    
    # original publication date:
    # fe.published(episode['published'] if 'published' in episode else '')
    fe.published(publication_dates['dates'][index])

    summary = episode['summary'] if 'summary' in episode else ''
    summary = "Originally published on %s\n%s" % (episode['published'][:-14], summary)
    fe.description(summary)
    fe.podcast.itunes_summary(summary)
    
    if 'content' in episode:
      for content in episode['content']:
        fe.content(content = content['value'] if 'value' in content else '',
                      #src  = content['base']  if 'base'  in content else '',
                      type = content['type']  if 'type'  in content else '')

    if 'media_content' in episode:
      for media in episode['media_content']:
        fe.enclosure(url   = media['url'] if 'url' in media else '',
                    length = media['filesize'] if 'filesize' in media else '',
                    type   = media['type'] if 'type' in media else '')

    if 'enclosure' in episode:
      for media in episode['enclosure']:
        fe.enclosure(url   = media['url'] if 'url' in media else '',
                    length = media['filesize'] if 'filesize' in media else '',
                    type   = media['type'] if 'type' in media else '')

    fe.link(href = episode['link'] if 'link' in episode else '', rel = 'alternate')
    for link in episode['links']:
      fe.link(rel = link['rel']  if 'rel'  in link else '',
              href = link['href'] if 'href' in link else '',
              type = link['type'] if 'type' in link else '')

    if 'image' in episode:
      fe.podcast.itunes_image(episode['image']['href'])

    fe.podcast.itunes_duration(episode['itunes_duration'] if 'itunes_duration' in episode else '')

  return fg.rss_str(pretty=True)