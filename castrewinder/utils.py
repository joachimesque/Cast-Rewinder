from . import app
from flask import request

import datetime
import json

from feedgen.feed import FeedGenerator
from dateutil import relativedelta


# https://stackoverflow.com/questions/11061058/using-htmlparser-in-python-3-2
from html.parser import HTMLParser
class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()




# UTILS

def get_frequency(request_form):
  """ Analyzes the form submitted, and parses the frequency
  """

  if request_form['frequency'] in ['daily', 'weekly', 'monthly']:
    frequency = request_form['frequency']
  elif request_form['frequency'] == 'weekdays':
    weekdays_frequency = []
    for form_element in request_form:
      if form_element[:-3] == 'weekday_':
        weekdays_frequency.append(form_element[-3:])

    frequency = '-'.join(weekdays_frequency)

  return frequency



def get_options(request_form):
  """ Analyzes the form submitted, and parses the options 
  """
  options = {}

  if int(request_form['option_limit']) > 1:
    options['start_at'] = request_form['option_limit'] 

  if request_form['option_format'] != 'feed_rss':
    options['format'] = request_form['option_format'] 

  if request_form['option_order'] != 'asc':
    options['order'] = request_form['option_order'] 

  return options


def parse_frequency(frequency, start_date):
  """ From the frequency and the start date, this function
      returns a dict with two keys
      publication_dates
          -> dates (all the dates from the start date to today, with the right frequency)
          -> limits (int, number of dates)
  """

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




def parse_options(options):
  """ From the frequency and the start date, this function
      returns a dict with as many keys as options
  """

  options_parsed = dict(o.split(':') for o in options.split(',')) if options != '' else {}

  return options_parsed



def generate_url(feed_id, frequency, options):
  """ Generates the feed URL
      with the feed ID and the frequency
      The start date is always today
  """
  start_date = datetime.datetime.now().strftime('%Y%m%d')
  
  options_string = ','.join(['%s:%s' % (key, o) for key, o in options.items()])

  if options:
    return "%s/%s/%s/%s" % (feed_id, frequency, start_date, options_string)
  
  else:
    return "%s/%s/%s" % (feed_id, frequency, start_date)


def build_feed(feed_object, feed_entries, publication_dates, feed_format='feed_rss'):
  """ From the Feed() and the Episodes(), with help from the publication dates dict
      gotten from parse_frequency(), this function makes the RSS feed.
  """
  feed = json.loads(feed_object.content)

  fg = FeedGenerator()

  fg.load_extension('podcast')

  fg.id(request.url)
  fg.title(feed['title'] if 'title' in feed else '')
  fg.subtitle(feed['subtitle'] if 'subtitle' in feed else '')

  fg.podcast.itunes_block(True)

  fg.link(href = request.url, rel = 'self')
  fg.link(href = feed['link'] if 'link' in feed else '', rel = 'alternate')
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
  fg.generator('Cast Rewinder & python-feedgen on %s' % request.host_url)

  if 'itunes_explicit' in feed and feed['itunes_explicit']:
    explicit = 'yes'
  else:
    explicit = 'no'
  fg.podcast.itunes_explicit(explicit)
  fg.podcast.itunes_new_feed_url(feed['itunes_new-feed-url'] if 'itunes_new-feed-url' in feed else '')
  fg.podcast.itunes_summary(feed['summary'] if 'summary' in feed else '')
  
  fg.description(strip_tags(feed['summary']) if 'summary' in feed
            else strip_tags(feed['description']) if 'description' in feed
            else strip_tags(feed['subtitle']) if 'subtitle' in feed
            else 'This feed was generated by Cast Rewinder on %s' % request.host_url)
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

    summary = strip_tags(html = episode['summary']) if 'summary' in episode else ''
    summary = "Originally published on %s\n%s" % (episode['published'][:-14], summary)
    fe.description(summary)
    fe.summary(summary)
    fe.podcast.itunes_summary(summary)
    
    if 'content' in episode:
      for content in episode['content']:
        fe.content(content = strip_tags(content['value']) if 'value' in content else '',
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
              type = link['type'] if 'type' in link else '',
              length = link['length'] if 'length' in link else '')

    if 'image' in episode:
      fe.podcast.itunes_image(episode['image']['href'])

    fe.podcast.itunes_duration(episode['itunes_duration'] if 'itunes_duration' in episode else '')

  if feed_format == 'feed_atom':
    return fg.atom_str(pretty=True)
  else:
    return fg.rss_str(pretty=True)