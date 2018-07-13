from . import app
from flask import request

import datetime
import json
import pytz

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




# WHEN PODCAST IS SUBMITTED

def get_frequency(request_form):
  """ Analyzes the form submitted, and parses the frequency
  """

  if request_form['frequency'] in ['daily', 'weekly', 'monthly']:
    frequency = request_form['frequency']
  elif request_form['frequency'] == 'custom_days':
    custom_days_frequency = []
    for key, value in request_form.items():
      if key[:-3] == 'custom_day_' and value is not False:
        custom_days_frequency.append(key[-3:])

    frequency = '-'.join(custom_days_frequency)

  return frequency



def get_options(request_form):
  """ Analyzes the form submitted, and parses the options 
  """
  options = {}

  if 'start_date' in request_form \
    and len(request_form['start_date']) == 10 \
    and int(request_form['start_date'][0:4]) > 2016 \
    and int(request_form['start_date'][5:7]) < 13 \
    and int(request_form['start_date'][8:]) < 32:
    options['start_date'] = ''.join(request_form['start_date'].split('-'))
  else:
    options['start_date'] = datetime.datetime.now().strftime('%Y%m%d')


  if 'start_date_timezone' in request_form:
    try:
      tz = pytz.timezone(request_form['start_date_timezone'])
    except:
      tz = pytz.timezone('Etc/UTC')
    tz_diff_from_UTC = datetime.datetime.now(tz).utcoffset().total_seconds()
    tz_sign = '+' if tz_diff_from_UTC > 0 else '-'
    tz_h, tz_m = divmod(abs(tz_diff_from_UTC) / 60, 60)

    options['start_date_timezone'] = "%s%02d%02d" % (tz_sign, tz_h, tz_m)
  else:
    options['start_date_timezone'] = '+0000'


  if ('option_limit', 'option_format', 'option_order') in request_form:

    if int(request_form['option_limit']) > 1:
      options['start_at'] = request_form['option_limit'] 

    if request_form['option_format'] != 'feed_rss':
      options['format'] = request_form['option_format'] 

    if request_form['option_order'] != 'asc':
      options['order'] = request_form['option_order'] 

  return options



def generate_url(feed_id, frequency, options):
  """ Generates the feed URL
      with the feed ID and the frequency
      The start date is always today
  """
  start_date = options.pop('start_date')

  start_date += options.pop('start_date_timezone')
  
  options_string = ','.join(['%s:%s' % (key, o) for key, o in options.items()])

  if options:
    return "%s/%s/%s/%s" % (feed_id, frequency, start_date, options_string)
  
  else:
    return "%s/%s/%s" % (feed_id, frequency, start_date)





# WHEN FEED IS CALLED

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

  try:
    start_datetime = datetime.datetime.strptime(str(start_date), '%Y%m%d%z')
  except ValueError:
    return False

  now = datetime.datetime.now().replace(tzinfo=start_datetime.tzinfo)

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
    # we start by checking if custom_days exist
    possible_custom_days = ['mon','tue','wed','thu','fri','sat','sun']
    custom_days_list = [possible_custom_days.index(x) + 1 for x in frequency.split('-') if x in possible_custom_days]

    # if today is not in the list of days, go back to the previous valid weekday
    # and add it to the list.
    if datetime.date.today().isoweekday() not in custom_days_list:
      for day in range(7):
        day_date = start_datetime + relativedelta.relativedelta(days=-day)
        if day_date.isoweekday() in custom_days_list:
          dates.append(day_date)
          break

    for day in range(delta.days + 1):
      # I add 1 to delta.days so it'll take today into account
      day_date = start_datetime + relativedelta.relativedelta(days=+day)
      if day_date.isoweekday() in custom_days_list:
        dates.append(day_date)

    limit = len(dates)

  return {'dates': dates, 'limit': limit}




def parse_options(options):
  """ From the frequency and the start date, this function
      returns a dict with as many keys as options
  """

  options_parsed = dict(o.split(':') for o in options.split(',')) if options != '' else {}

  return options_parsed



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
  if 'links' in feed:
    for link in feed['links']:
      fg.link(rel  = link['rel']  if 'rel'  in link else '',
              type = link['type'] if 'type' in link else '',
              href = link['href'] if 'href' in link else '')

  if 'author_detail' in feed:
    fg.author(name  = feed['author_detail']['name']  if 'name'  in feed['author_detail'] else '',
              email = feed['author_detail']['email'] if 'email' in feed['author_detail'] else '')
  if 'authors' in feed:
    for author in feed['authors']:
      fg.author(name  = author['name']  if 'name'  in author else '',
                email = author['email'] if 'email' in author else '')

  if 'image' in feed and 'href' in feed['image']:
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
  
  fg.description(strip_tags(feed['summary']) if 'summary' in feed and feed['summary'] != ''
            else strip_tags(feed['description']) if 'description' in feed and feed['description'] != ''
            else strip_tags(feed['subtitle']) if 'subtitle' in feed and feed['subtitle'] != ''
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

    episode_pubished = '-'.join((str(episode['published_parsed'][0]),  # year
                                 str(episode['published_parsed'][1]).zfill(2),  # month
                                 str(episode['published_parsed'][2]).zfill(2))) # day

    summary = strip_tags(html = episode['summary']) if 'summary' in episode else ''
    summary = "Originally published on %s\n%s" % (episode_pubished, summary)
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
    if 'links' in episode:
      for link in episode['links']:
        fe.link(rel = link['rel']  if 'rel'  in link else '',
                href = link['href'] if 'href' in link else '',
                type = link['type'] if 'type' in link else '',
                length = link['length'] if 'length' in link else '')

    if 'image' in episode and 'href' in episode['image']:
      image_url = episode['image']['href']
      if image_url.rfind('?') > 0:
        image_url = image_url[:image_url.rfind('?')]
      if image_url[-4:] in ('.jpg', '.png'):
        fe.podcast.itunes_image(image_url)



    fe.podcast.itunes_duration(episode['itunes_duration'] if 'itunes_duration' in episode else '')

  if feed_format == 'feed_atom':
    return fg.atom_str(pretty=True)
  else:
    return fg.rss_str(pretty=True)