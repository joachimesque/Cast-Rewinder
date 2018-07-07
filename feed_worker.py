# -*- coding: utf-8 -*-
import argparse
import datetime
import calendar
import time
import json
import sys
from requests import get
from urllib.parse import urlparse

import feedparser

from castrewinder import db
from castrewinder.models import Feed, Episode


def to_datetime_from_structtime(time_tuple):
  """ Converts structtime elements to good old datetime """
  return datetime.datetime.fromtimestamp(time.mktime(time_tuple))

def json_serial(obj):
  """ JSON serializer for objects not serializable by default json code """

  if isinstance(obj, (datetime.datetime, datetime.date)):
    return obj.isoformat()
  if isinstance(obj, (datetime.timedelta)):
    return str(obj)
  raise TypeError ("Type %s not serializable" % type(obj))


def add_feed_to_db(feed, feed_url):
  """ Adds a feed to the Feed Table
      When a new feed is added, the last updated value is 0
      So that all the entries will be added to the DB
  """
  last_published_element = datetime.datetime.fromtimestamp(0)
  new_feed = Feed(url = feed_url,
                  last_published_element = last_published_element,
                  content = json.dumps(feed.feed, default=json_serial))
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

  for entry in feed.entries:
    published = to_datetime_from_structtime(time_tuple = entry.published_parsed)
    
    if feed_object.last_published_element < published or ignore_date == True:
      new_entry = Episode(published = published,
                          content = json.dumps(entry, default=json_serial),
                          feed_id = feed_object.id)
      db.session.add(new_entry)

  if not ignore_date:
    # updates the last updated value in the parent Feed in DB
    last_published_element = to_datetime_from_structtime(time_tuple = feed.entries[0].published_parsed)
    feed_object.last_published_element = last_published_element

  db.session.commit()


def ask_for_url():
  # Command-line helper to ask for an URL
  print("Please specify the URL of a feed to import:")
  url = input(">>> ")
  import_feed(url)

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

    # Check if the URL is already present in the Feed Table
    url_exists_in_db = bool(db.session.query(Feed).filter(Feed.url == feed_url).count())

    feed = feedparser.parse(feed_url)

    if feed['entries'] == []:
      # Cancel operation if the feed doesn't have any entries
      # Like if it's a normal webpage
      return False

    if not url_exists_in_db:
      # Don't populate the Feed Table if it already contains the feed
      add_feed_to_db(feed = feed, feed_url = feed_url)

    # Populate the Episode Table
    add_entries_to_db(feed = feed, feed_url = feed_url, ignore_date = ignore_date)

    # Not that useful.
    # if 'links' in feed.feed:
    #   for link in feed.feed.links:
    #     if link.rel == 'next':
    #       print(str(link), file=sys.stderr)

    #       import_feed(url = link.href, ignore_date = True)

    return True

  else:
    print("The specified URL is not valid. Please verify you have the 'HTTP' part.")
    ask_for_url()

def update_feeds():
  """ Feed updater, meant to be used in a cron """

  # This will get all the feeds
  all_feeds = db.session.query(Feed).all()

  # For each feed, get the updated feed and populate the db
  for feed_object in all_feeds:
    feed = feedparser.parse(feed_object.url)
    add_entries_to_db(feed = feed, feed_url = feed_object.url)

  return True


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='You can import feeds into Cast Rewinder.',
                                    prog='Cast Rewinder')
  parser.add_argument('-f','--feed_url',help='''Specify an URL to import''')
  parser.add_argument('-u','--update_feeds',help='''Updates all feeds''', action='store_true')

  args = parser.parse_args()

  if args.feed_url:
    import_feed(url = args.feed_url)

  if args.update_feeds:
    update_feeds()

  if not any(vars(args).values()):
    ask_for_url()