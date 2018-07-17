# -*- coding: utf-8 -*-
import argparse
import datetime
import calendar
import time
import json
from requests import get
from dateutil import parser
from urllib.parse import urlparse

import feedparser

from castrewinder import db
from castrewinder.models import Feed, Episode

running_from_command_line = False

def to_datetime_from_structtime(time_tuple):
  """ Converts structtime elements to good old datetime """
  return datetime.datetime.fromtimestamp(time.mktime(tuple(time_tuple)))

def json_serial(obj):
  """ JSON serializer for objects not serializable by default json code """

  if isinstance(obj, (datetime.datetime, datetime.date)):
    return obj.isoformat()
  if isinstance(obj, (datetime.timedelta)):
    return str(obj)
  raise TypeError ("Type %s not serializable" % type(obj))


def add_feed_to_db(feed, feed_url, response_headers = (None,None)):
  """ Adds a feed to the Feed Table
      When a new feed is added, the last updated value is 0
      So that all the entries will be added to the DB
  """
  last_published_element = datetime.datetime.fromtimestamp(0)
  new_feed = Feed(url = feed_url,
                  etag = response_headers[0],
                  last_modified = response_headers[1],
                  last_published_element = last_published_element,
                  content = json.dumps(feed['feed'], default=json_serial))
  db.session.add(new_feed)
  db.session.commit()
  return True

def add_entries_to_db(feed, feed_url, ignore_date = False):
  """ Adds entries to the Episode Table
      For each entry in the feed, it will:
      - check the last updated in the parent Feed in DB
      - insert a new Episode in the table if not already present
      Then it updates the last updated value in the parent Feed in DB
      Conditions can be forced if we want to ignore the date
  """
  feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

  for entry in feed['entries']:
    published = to_datetime_from_structtime(time_tuple = entry['published_parsed'])
    
    if feed_object.last_published_element < published or ignore_date == True:
      new_entry = Episode(published = published,
                          content = json.dumps(entry, default=json_serial),
                          feed_id = feed_object.id)
      db.session.add(new_entry)

  if not ignore_date:
    # updates the last updated value in the parent Feed in DB
    feed_object.last_published_element = datetime.datetime.today()

  db.session.commit()


def ask_for_url():
  # Command-line helper to ask for an URL
  print("Please specify the URL of a feed to import:")
  url = input(">>> ")
  import_feed(url)



    
def check_url(url):
  u = urlparse(url = url)

  feed_url = url

  if u.netloc == 'itunes.apple.com':
    feed_url = get_feed_from_itunes_api(itunes_url = url)

  if u.netloc.endswith('soundcloud.com'):
    feed_url = get_feed_from_soundcloud_url(soundcloud_url = url)

  return feed_url


def get_feed_from_itunes_api(itunes_url):
  """ Helper that will get the right URL from iTunes Podcast URL
      thanks to the iTunes lookup public API
      and the magic of JSON
  """
  itunes_id = urlparse(itunes_url).path.split('/')[-1][2:]
  itunes_query = "https://itunes.apple.com/lookup?id=%s&entity=podcast" % itunes_id
  try:
      response = get(itunes_query)
  except Exception:
      print("Error: Something happened with the connection that prevented us to get %s’s info" % itunes_id)
      return None

  # if there's a bad ID, iTunes returns us {'resultCount': 0, 'results': []}
  if json.loads(response.text)['resultCount'] > 0:
    # returns the feedUrl element of the first result.
    return json.loads(response.text)['results'][0]['feedUrl']
  else:
    print("Error: the specified iTunes URL does not match iTune’s contents. Please check if you did it well.")
    return None


def get_feed_from_soundcloud_url(soundcloud_url):
  """ Helper that will get the right URL from a soundcloud page
      For that we’ll parse the user page
  """
  soundcloud_profile = urlparse(soundcloud_url).path.split('/')[1]
  soundcloud_query = "https://soundcloud.com/%s/" % soundcloud_profile
  try:
      response = get(soundcloud_query)
  except Exception:
      print("Error: Something happened with the connection that prevented us to get %s’s info" % soundcloud_profile)
      return None

  index_beg = response.text.find('soundcloud://users')
  index_end = response.text.find('"', index_beg)

  soundcloud_id = response.text[index_beg + 13:index_end]
  soundcloud_feed_url = 'http://feeds.soundcloud.com/users/soundcloud:%s/sounds.rss' % soundcloud_id

  return soundcloud_feed_url


def import_feed(url, ignore_date = False):
  """ Feed importer, called from the web app.
      It will verify that the URL is ok,
      check the right URL if it’s an iTunes URL
      that the feed is a RSS/Atom feed (if there are entries)
      It will then
      - Populate the db with the feed if it's new
      - Populate the db with entries
  """
  u = urlparse(url = url)

  if bool(u.scheme):
    feed_url = u.geturl()

    # More checks might come
    if u.netloc == 'itunes.apple.com':
      feed_url = get_feed_from_itunes_api(itunes_url = feed_url)
    if u.netloc.endswith('soundcloud.com') and u.netloc != 'feeds.soundcloud.com':
      soundcloud_url = get_feed_from_soundcloud_url(soundcloud_url = feed_url)
      if soundcloud_url:
        feed_url = soundcloud_url

    headers = {
      'Accept': 'text/xml,application/rss+xml,application/atom+xml,application/json;q=0.9,*/*;q=0.8',
      'User-Agent': 'Cast Rewinder on rewind.website'
      }

    # Check if the URL is already present in the Feed Table
    url_exists_in_db = bool(db.session.query(Feed).filter(Feed.url == feed_url).count())

    if url_exists_in_db:
      feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()
      if feed_object.etag:
        headers['If-None-Match'] = feed_object.etag
      if feed_object.last_modified:
        headers['If-Modified-Since'] = feed_object.last_modified

    try:
      response = get(feed_url, headers=headers)
    except Exception:
      print("Error: Something happened with the connection that prevented us to get the feed")
      return False

    if response.status_code == 304:
      # 304 Not Modified gets a pass
      return True

    if response.text == '':
      # Empty response raises all hell
      return False

    response_content_type = response.headers.get('content-type', '').split(';')[0]

    feed = []
    if response_content_type == 'application/json':
      # transform json feed object to feedparser object
      feed = get_parsed_json_feed(json_feed = response.text)
    elif response_content_type in ('text/xml','application/rss+xml','application/atom+xml','application/xml','application/xhtml+xml',''):
      # We allow NO Content-Type headers. Yeah, I know.
      feed = feedparser.parse(response.text)
    else:
      # bad headers raise all hell
      return False

    if feed == [] or feed['entries'] == []:
      # Cancel operation if the feed doesn't have any entries
      # Like if it's a normal webpage
      return False

    if url_exists_in_db:
      # Just update the Feed with new ETag and Content Type
      if 'ETag' in response.headers:
        feed_object.etag = response.headers.get('ETag', None)
      if 'Last-Modified' in response.headers:
        feed_object.last_modified = response.headers.get('Last-Modified', None)
      db.session.commit()

    else:
      # Don't populate the Feed Table if it already contains the feed
      response_headers = (response.headers.get('ETag', None), response.headers.get('Content-Type', None))
      add_feed_to_db(feed = feed, feed_url = feed_url, response_headers = response_headers)

    # Populate the Episode Table
    add_entries_to_db(feed = feed, feed_url = feed_url, ignore_date = ignore_date)

    return True

  else:
    if running_from_command_line:
      print("The specified URL is not valid. Please verify you have the 'HTTP' part.")
      ask_for_url()
    else:
      return False

def get_parsed_json_feed(json_feed):

  if json_feed == None or json_feed =='':
    return []

  json_feed_as_json = json.loads(json_feed)


  feed = {
    "title": json_feed_as_json.get('title', ''),
    "links": [
      {
        "rel": "alternate",
        "type": "text/html",
        "href": json_feed_as_json.get('home_page_url', '')
      },
      {
        "rel": "self",
        "type": "application/rss+xml",
        "href": json_feed_as_json.get('feed_url', '')
      },
    ],
    "link": json_feed_as_json.get('home_page_url', ''),
    "language": "en",
    "rights": "",
    "subtitle": "",
    "image": {
      "href": json_feed_as_json.get('icon', '')
    },
    "summary": json_feed_as_json.get('description', '')
  }

  if "author" in json_feed_as_json:
    feed["author"] = json_feed_as_json['author'].get('name', ''),
    feed["author_detail"] = {
      "name": json_feed_as_json['author'].get('name', ''),
      "url": json_feed_as_json['author'].get('url', '')
    },


  episodes = []

  for item in json_feed_as_json.get('items', []):
    episode = {
      "id": item.get('id', ''),
      "title": item.get('title', ''),
      "link": item.get('url', ''),
      "summary": item.get('summary', ''),
      "content": [
        {
          "type": "text/plain",
          "value": item.get('content_text', '')
        },
        {
          "type": "text/html",
          "value": item.get('content_html', '')
        }
      ],
      "image": {
        "href": item.get('image', '')
      },
      "media_content": []
    }

    for attachment in item.get('attachments', []):
      enclosure = {
          "url": attachment.get('url', ''),
          "type": attachment.get('mime_type', ''),
          "filesize": attachment.get('size_in_bytes', '')
        }
      episode['media_content'].append(enclosure)

    date_published = parser.parse(item.get('date_published', ''))

    episode["published"] = str(date_published)
    episode["published_parsed"] = list(date_published.timetuple())

    episodes.append(episode)

  return {
    'feed': feed,
    'entries': episodes
    }



def update_feeds():
  """ Feed updater, meant to be used in a cron """

  # This will get all the feeds
  all_feeds = db.session.query(Feed).all()

  # For each feed, get the updated feed and populate the db
  for feed_object in all_feeds:

    headers = {
      'Accept': 'text/xml,application/rss+xml,application/atom+xml,application/json;q=0.9,*/*;q=0.8',
      'User-Agent': 'Cast Rewinder on rewind.website'
      }

    if feed_object.etag:
      headers['If-None-Match'] = feed_object.etag
    if feed_object.last_modified:
      headers['If-Modified-Since'] = feed_object.last_modified

    try:
      response = get(feed_object.url, headers=headers)
    except Exception:
      print("Error: Something happened with the connection that prevented us to get the feed")
      continue

    if response.status_code == 304 or response.text == '':
      # 304 Not Modified or empty responses get a pass
      continue

    response_content_type = response.headers.get('content-type', '').split(';')[0]

    feed = []
    if response_content_type == 'application/json':
      # transform json feed object to feedparser object
      feed = get_parsed_json_feed(json_feed = response.text)
    elif response_content_type in ('text/xml','application/rss+xml','application/atom+xml','application/xml','application/xhtml+xml',''):
      # We allow NO Content-Type headers. Yeah, I know.
      feed = feedparser.parse(response.text)
    else:
      # bad headers get a pass
      continue

    if feed == []:
      # empty feeds get a pass
      continue

    if 'ETag' in response.headers:
      feed_object.etag = response.headers.get('ETag', None)
    if 'Last-Modified' in response.headers:
      feed_object.last_modified = response.headers.get('Last-Modified', None)

    db.session.commit()

    add_entries_to_db(feed = feed, feed_url = feed_object.url)

  return True


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='You can import feeds into Cast Rewinder.',
                                    prog='Cast Rewinder')
  parser.add_argument('-f','--feed_url',help='''Specify an URL to import''')
  parser.add_argument('-u','--update_feeds',help='''Updates all feeds''', action='store_true')

  args = parser.parse_args()

  running_from_command_line = True

  if args.feed_url:
    import_feed(url = args.feed_url)

  if args.update_feeds:
    update_feeds()

  if not any(vars(args).values()):
    ask_for_url()