# -*- coding: utf-8 -*-
import argparse
import datetime
import calendar
import time
import json
from requests import get, head
from dateutil import parser
from urllib.parse import urlparse

from textwrap import TextWrapper

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

  for entry in reversed(feed['entries']):
    try:
      published = to_datetime_from_structtime(time_tuple = entry['published_parsed'])
    except:
      published = datetime.datetime.today()

    enclosure_url = get_enclosure_url_from_episode_content(content = entry)

    # # Calling the enclosure url status is too costly as of yet
    # enclosure_status = get_url_status(url = enclosure_url)
    # # If there was 301s, set last URL
    # if enclosure_status[1] != '':
    #   enclosure_url = enclosure_status[1]

    if feed_object.last_published_element < published or ignore_date == True:
      new_entry = Episode(published = published,
                          content = json.dumps(entry, default=json_serial),
                          feed_id = feed_object.id,
                          enclosure_url = enclosure_url,
                          # enclosure_is_active = enclosure_status[0])
                          enclosure_is_active = True)
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

  response_text = json.loads(response.text)

  # if there's a bad ID, iTunes returns us {'resultCount': 0, 'results': []}
  if 'resultCount' in response_text and response_text['resultCount'] > 0:
    # returns the feedUrl element of the first result.
    return response_text['results'][0]['feedUrl']
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

def get_feed_url(feed_id):
  feed = db.session.query(Feed).get(feed_id)
  return feed.url if feed else None

def get_feed_id(feed_url):
  try:
    feed = db.session.query(Feed).filter(Feed.url == feed_url).one()
  except Exception:
    return None

  return feed.id

def reset_feed(feed):
  """ Feed Reset, called from the command line.
      feed can be a feed URL or a feed ID from the database.

  """
  try:
    feed = int(feed)
    print("Feed ID given: %s" % feed)
    feed_id = feed
    feed_url = get_feed_url(feed_id = feed_id)

  except ValueError:
    print("Feed URL given: %s" % feed)
    feed_url = feed
    feed_id = get_feed_id(feed_url = feed_url)

  if not feed_id or not feed_url:
    exit('The feed your provided (%s) is not in the database.' % feed)

  print('Feed %s (URL: %s) is going to be reset. Do you wish to do it?' % (feed_id, feed_url))
  user_response = input('y/N >>> ')

  if user_response == 'y' or user_response == 'yes':
    d = db.session.query(Episode).filter(Episode.feed_id == feed_id)
    d.delete()
    db.session.commit()

    import_feed(url = feed_url, ignore_conditional_loading = True, ignore_date = True)

    print('The reset seems to have gone successfully.')
  
  else:
    print('Aborting operation.')


def which_feed(url):
  feed_id = get_feed_id(feed_url = url)

  if not feed_id:
    exit('The feed your provided (%s) is not in the database.' % feed)
  else:
    print('Feed ID: %s' % feed)


def feed_info(feed):

  try:
    feed_id = int(feed)
    print("Feed ID given: %s" % feed)

  except ValueError:
    print("Feed URL given: %s" % feed)
    feed_id = get_feed_id(feed_url = feed)

  if not feed_id:
    print('The feed URL your provided (%s) is not in the database.' % feed)
  else:
    feed_object = db.session.query(Feed).get(feed_id)

    if not feed_object:
      print('The feed ID your provided (%s) is not in the database.' % feed)

    else:
      feed_content = json.loads(feed_object.content)
      feed_episodes = db.session.query(Episode).filter(Episode.feed_id == feed_id).count()

      wrapper = TextWrapper(width=66)
      feed_summary = "\n              ".join(wrapper.wrap(feed_content['summary']))


      print("\nFeed ID:      %s" \
            "\nFeed URL:     %s" \
            "\nFeed Name:    %s" \
            "\nLast Grabbed: %s" \
            "\nSummary:      %s" \
            "\nEpisodes #:   %s" \
             % (feed_id,
                feed_object.url,
                feed_content['title'],
                feed_object.last_published_element,
                feed_summary,
                feed_episodes))

def import_feed(url, ignore_date = False, ignore_conditional_loading = False):
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
      # We only add etag/last_modified headers if we don't `ignore_conditional_loading`
      feed_object = db.session.query(Feed).filter(Feed.url == feed_url).one()
      if feed_object.etag and not ignore_conditional_loading:
        headers['If-None-Match'] = feed_object.etag
      if feed_object.last_modified and not ignore_conditional_loading:
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

    # check if a BOM is at the start of the file, like http://www.wizards.com/dnd/rsspodcast.xml
    if response.text[0] == u'\ufeff' or response.text[0] == u'\xef':  # bytes \xef\xbb\xbf in utf-8 encoding
        response.encoding = 'utf-8-sig'

    response_content_type = response.headers.get('content-type', '').split(';')[0]

    # create the feed object
    feed = []
    # depending on the response headers we call a different parser for the feed
    if response_content_type == 'application/json':
      # transform json feed object to feedparser object
      feed = get_parsed_json_feed(json_feed = response.text)
    elif response_content_type in ('text/xml',
                                  'application/rss+xml',
                                  'application/atom+xml',
                                  'application/xml+rss',
                                  'application/xml+atom',
                                  'application/xml',
                                  'application/xhtml+xml',
                                  'application/xml+xhtml',
                                  ''):
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
      # Check if feed info has been updated, update it if necessary
      feed_content_as_json = json.dumps(feed['feed'], default=json_serial)
      if feed_content_as_json != feed_object.content:
        feed_object.content = feed_content_as_json

      # Update the Feed with new ETag and Content Type
      if 'ETag' in response.headers:
        feed_object.etag = response.headers.get('ETag', None)
      if 'Last-Modified' in response.headers:
        feed_object.last_modified = response.headers.get('Last-Modified', None)
      db.session.commit()

    else:
      # Don't populate the Feed Table if it already contains the feed
      response_headers = (response.headers.get('ETag', None), response.headers.get('Last-Modified', None))
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

    feed_object.content = json.dumps(feed['feed'], default=json_serial)

    db.session.commit()

    add_entries_to_db(feed = feed, feed_url = feed_object.url)

  return True

def verify_links():
  """ This goes through every podcast file link
      and checks if it’s still available"""

  all_episodes = db.session.query(Episode).filter(Episode.enclosure_is_active == True).all()

  for episode in all_episodes:

    # If there's no enclosure_url specified
    if not episode.enclosure_url:
      # Gets the enclosure URL and sets in in DB
      enclosure_url = get_enclosure_url_from_episode_content(content = json.loads(episode.content))
      episode.enclosure_url = enclosure_url

    enclosure_status = get_url_status(url = episode.enclosure_url)

    # If there was 301s, the second part of the tuple is defined,
    # set it as the enclosure URL
    if enclosure_status[1] != '':
      episode.enclosure_url = enclosure_status[1]

    # Set status active/inactive in DB
    episode.enclosure_is_active = enclosure_status[0]

  db.session.commit()

  return True

def get_url_status(url):
  # Gets the head of a request, and returns a tuple with 2 items:
  # - False if anything other than 2xx-3xx
  # - new URL if 301, '' if none

  try:
    request_head = head(url, allow_redirects=True)
  except Exception:
    return (False, '')

  # check history for 301
  end_url = ''
  history_codes = [resp.status_code for resp in reversed(request_head.history)]
  if 301 in history_codes and 302 not in history_codes:
    # the last occurence of 301 is the first index (bc history is reversed)
    last_301 = history_codes.index(301)
    end_url = request_head.url

  return (True, end_url) if request_head.status_code == 200 else (False, None)


def get_enclosure_url_from_episode_content(content):
  # Traverses an episode content element for enclosures
  # RSS (or JSON Feed)
  for enclosure in reversed(content.get('enclosure', [])):
    # Only get the LAST enclosure of the post (as per RSS recommendations)
    if enclosure.get('type') != 'application/x-shockwave-flash':
      return enclosure.get('url')

  # Atom
  for link in content.get('links', []):
    # Only get the first link[rel="enclosure"] of the post
    if link.get('rel') == 'enclosure' \
      and link.get('type') != 'application/x-shockwave-flash':
      return link.get('href')

  # if no <enclosure> and no link[rel="enclosure"], return False
  return None


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='You can import feeds into Cast Rewinder.',
                                    prog='Cast Rewinder')
  parser.add_argument('-i','--import_feed',help='''Specify an URL to import''')
  parser.add_argument('-r','--reset_feed',help='''Reset a feed''')
  parser.add_argument('-w','--which_feed',help='''Get a feed’s ID from URL''')
  parser.add_argument('--feed_info',help='''Get a feed’s info from ID''')
  parser.add_argument('-u','--update_feeds',help='''Updates all feeds''', action='store_true')
  parser.add_argument('-l','--verify_links',help='''Check all podcast links''', action='store_true')

  args = parser.parse_args()

  running_from_command_line = True

  if args.import_feed:
    import_feed(url = args.import_feed)

  if args.reset_feed:
    reset_feed(feed = args.reset_feed)

  if args.which_feed:
    which_feed(url = args.which_feed)

  if args.feed_info:
    feed_info(feed = args.feed_info)

  if args.update_feeds:
    update_feeds()

  if args.verify_links:
    verify_links()

  if not any(vars(args).values()):
    ask_for_url()