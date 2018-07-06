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
    return datetime.datetime.fromtimestamp(time.mktime(time_tuple))

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    if isinstance(obj, (datetime.timedelta)):
        return str(obj)
    raise TypeError ("Type %s not serializable" % type(obj))


def add_feed_to_db(feed, feed_url):
  last_published_element = datetime.datetime.fromtimestamp(0)
  new_feed = Feed(url = feed_url,
                  last_published_element = last_published_element,
                  content = json.dumps(feed.feed, default=json_serial))
  db.session.add(new_feed)
  db.session.commit()
  return True

def add_entries_to_db(feed, feed_url, ignore_date = False):
  feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()

  for entry in feed.entries:
    published = to_datetime_from_structtime(time_tuple = entry.published_parsed)
    
    if feed_object.last_published_element < published or ignore_date == True:
      new_entry = Episode(published = published,
                          content = json.dumps(entry, default=json_serial),
                          feed_id = feed_object.id)
      db.session.add(new_entry)

  if not ignore_date and len(feed.entries) > 0:
    last_published_element = to_datetime_from_structtime(time_tuple = feed.entries[0].published_parsed)
    feed_object.last_published_element = last_published_element

  db.session.commit()


def ask_for_url():
  print("Please specify the URL of a feed to import:")
  url = input(">>> ")
  import_feed(url)

def get_feed_from_itunes_api(itunes_url):
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

def get_feed(feed_url):
  if feed_url:
    feed = feedparser.parse(feed_url)
    return feed
  else:
    ask_for_url()

def import_feed(url, ignore_date = False):
  u = urlparse(url = url)

  if bool(u.scheme):
    feed_url = u.geturl()
    print("Importing from: %s" % u.geturl())

    if u.netloc == 'itunes.apple.com':
      feed_url = get_feed_from_itunes_api(itunes_url = feed_url)


    url_exists_in_db = bool(db.session.query(Feed).filter(Feed.url == feed_url).count())

    feed = get_feed(feed_url = feed_url)

    if not url_exists_in_db:
      add_feed_to_db(feed = feed, feed_url = feed_url)

    add_entries_to_db(feed = feed, feed_url = feed_url, ignore_date = ignore_date)

    # Not that useful.
    # if 'links' in feed.feed:
    #   for link in feed.feed.links:
    #     if link.rel == 'next':
    #       print(str(link), file=sys.stderr)

    #       import_feed(url = link.href, ignore_date = True)

  else:
    print("The specified URL is not valid. Please verify you have the 'HTTP' part.")
    ask_for_url()

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='You can import feeds into Cast Rewinder.',
                                    prog='Cast Rewinder')
  parser.add_argument('-f','--feed_url',help='''Specify an URL to import''')

  args = parser.parse_args()

  if args.feed_url:
    import_feed(url = args.feed_url)

  if not any(vars(args).values()):
    ask_for_url()