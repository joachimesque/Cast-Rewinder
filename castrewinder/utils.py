from . import app
from flask import request

import datetime
import json
import pytz

from feedgen.feed import FeedGenerator
from dateutil import relativedelta, parser


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

# from https://stackoverflow.com/questions/1703546/parsing-date-time-string-with-timezone-abbreviated-name-in-python
tz_str = '''-12 Y
-11 X NUT SST
-10 W CKT HAST HST TAHT TKT
-9 V AKST GAMT GIT HADT HNY
-8 U AKDT CIST HAY HNP PST PT
-7 T HAP HNR MST PDT
-6 S CST EAST GALT HAR HNC MDT
-5 R CDT COT EASST ECT EST ET HAC HNE PET
-4 Q AST BOT CLT COST EDT FKT GYT HAE HNA PYT
-3 P ADT ART BRT CLST FKST GFT HAA PMST PYST SRT UYT WGT
-2 O BRST FNT PMDT UYST WGST
-1 N AZOT CVT EGT
0 Z EGST GMT UTC WET WT
1 A CET DFT WAT WEDT WEST
2 B CAT CEDT CEST EET SAST WAST
3 C EAT EEDT EEST IDT MSK
4 D AMT AZT GET GST KUYT MSD MUT RET SAMT SCT
5 E AMST AQTT AZST HMT MAWT MVT PKT TFT TJT TMT UZT YEKT
6 F ALMT BIOT BTT IOT KGT NOVT OMST YEKST
7 G CXT DAVT HOVT ICT KRAT NOVST OMSST THA WIB
8 H ACT AWST BDT BNT CAST HKT IRKT KRAST MYT PHT SGT ULAT WITA WST
9 I AWDT IRKST JST KST PWT TLT WDT WIT YAKT
10 K AEST ChST PGT VLAT YAKST YAPT
11 L AEDT LHDT MAGT NCT PONT SBT VLAST VUT
12 M ANAST ANAT FJT GILT MAGST MHT NZST PETST PETT TVT WFT
13 FJST NZDT
11.5 NFT
10.5 ACDT LHST
9.5 ACST
6.5 CCT MMT
5.75 NPT
5.5 SLT
4.5 AFT IRDT
3.5 IRST
-2.5 HAT NDT
-3.5 HNT NST NT
-4.5 HLV VET
-9.5 MART MIT'''

tzd = {}
for tz_descr in map(str.split, tz_str.split('\n')):
    tz_offset = int(float(tz_descr[0]) * 3600)
    for tz_code in tz_descr[1:]:
        tzd[tz_code] = tz_offset

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



  if 'option_start_at' in request_form:
    if int(request_form['option_start_at']) > 1:
      options['start_at'] = request_form['option_start_at'] 

  if 'option_format' in request_form:
    if request_form['option_format'] in ('feed_atom', 'feed_json'):
      options['format'] = request_form['option_format'] 

  if 'option_order' in request_form:
    if request_form['option_order'] in ('desc'):
      options['order'] = request_form['option_order'] 

  if 'option_keepdates' in request_form:
    if request_form['option_keepdates'] or request_form['option_keepdates'] == 'true':
      options['keep_dates'] = 'yes'

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

  now = datetime.datetime.now(start_datetime.tzinfo)

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
    for day in range(7):
      day_date = start_datetime + relativedelta.relativedelta(days=-1 * (day + 1))
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



def build_xml_feed(feed_object, feed_entries, publication_dates, options, feed_format='feed_rss'):
  """ From the Feed() and the Episodes(), with help from the publication dates dict
      gotten from parse_frequency(), this function makes the RSS feed.
  """
  feed = json.loads(feed_object.content)

  fg = FeedGenerator()

  fg.load_extension('podcast')

  fg.id(request.url)
  fg.title(feed.get('title', ''))
  fg.subtitle(feed.get('subtitle', ''))

  fg.podcast.itunes_block(True)

  link = feed.get('link')
  if link == '':
    # This would be the perfect place
    # to link to a special HTML format feed. TODO.
    link = request.url
  links = [
    { 'href': request.url,
      'rel' : 'self'},
    { 'href': link,
      'rel' : 'alternate'}
    ]
  for link in feed.get('links', []):
    if link.get('href', '') != '':
      links.append({
              'rel' : link.get('rel', ''),
              'type': link.get('type', ''),
              'href': link.get('href', '')})
  fg.link(links)


  if 'author_detail' in feed:
    fg.author(name  = feed['author_detail'].get('name', ''),
              email = feed['author_detail'].get('email', ''))
  for author in feed.get('authors', []):
    fg.author(name  = author.get('name', '') ,
              email = author.get('email', ''))

  fg.language(feed.get('language', ''))
  fg.rights(feed.get('rights', ''))
  fg.generator('Cast Rewinder & python-feedgen on %s' % request.host_url)

  if feed.get('itunes_explicit'):
    explicit = 'yes'
  else:
    explicit = 'no'
  fg.podcast.itunes_explicit(explicit)
  fg.podcast.itunes_summary(feed.get('summary', ''))
  
  fg.description(strip_tags(feed['summary']) if 'summary' in feed and feed['summary'] != ''
            else strip_tags(feed['description']) if 'description' in feed and feed['description'] != ''
            else strip_tags(feed['subtitle']) if 'subtitle' in feed and feed['subtitle'] != ''
            else 'This feed was generated by Cast Rewinder on %s' % request.host_url)
  # fg.podcast.itunes_type(feed['itunes_type'])

  if publication_dates['limit'] > 0:
    if 'image' in json.loads(feed_entries[0].content) and 'href' in json.loads(feed_entries[0].content)['image']:
      image_url = json.loads(feed_entries[0].content)['image']['href']
      if image_url.rfind('?') > 0:
        image_url = image_url[:image_url.rfind('?')]
      if image_url[-4:] in ('.jpg', '.png'):
        fg.podcast.itunes_image(image_url)


  if 'image' in feed and 'href' in feed['image']:
    fg.image(feed['image']['href'])


  for index, entry in enumerate(feed_entries):
    episode = json.loads(entry.content)

    fe = fg.add_entry()
    fe.id("castrewinder_%s_%s" % (request.url, episode.get('id', '')))
    fe.title(episode.get('title', ''))
    fe.podcast.itunes_subtitle(episode.get('subtitle', ''))
    
    summary = strip_tags(html = episode.get('summary', ''))

    if 'keep_dates' in options and options['keep_dates'] == 'yes':
      fe.published(
        parser.parse(
          episode.get('published', ''),
          tzinfos=tzd
        ).isoformat()
      )
    else:
      fe.published(publication_dates['dates'][index])
      if 'published_parsed' in episode and episode['published_parsed'] != None:
        episode_published = '-'.join((str(episode['published_parsed'][0]),  # year
                                     str(episode['published_parsed'][1]).zfill(2),  # month
                                     str(episode['published_parsed'][2]).zfill(2))) # day
        summary = "Originally published on %s\n%s" % (episode_published, summary)

    fe.description(summary)
    fe.summary(summary)
    fe.podcast.itunes_summary(summary)
    
    for content in episode.get('content', []):
      fe.content(content = strip_tags(content['value']) if 'value' in content else '',
                    type = content['type']  if 'type'  in content else '')

    if entry.enclosure_is_active:
      # don't add an enclosure or media if the enclosure link is not active
      for media in episode.get('media_content', []):
        if media.get('type') != 'application/x-shockwave-flash':
          fe.enclosure(url   = media.get('url', ''),
                      length = str(media.get('filesize', '')),
                      type   = media.get('type', ''))

      for enclosure in episode.get('enclosure', []):
        if enclosure.get('type') != 'application/x-shockwave-flash':
          fe.enclosure(url   = enclosure.get('url', ''),
                      length = str(enclosure.get('filesize', '')),
                      type   = enclosure.get('type', ''))

    link = episode.get('link', '')
    if link == '':
      link = feed.get('link')
      # This would be the perfect place
    if link == '':
      # to link to a special HTML format feed. TODO.
      link = "%s#%s" % (request.url, "castrewinder_%s_%s" % (request.url, episode.get('id', '')))

    links = [{'href': link, 'rel': 'alternate'}]

    for link in episode.get('links', []):
      if link.get('href','') != '':
        if link.get('rel') == 'enclosure':
          if entry.enclosure_is_active:
            links.append({'rel'   : 'enclosure',
                          'href'  : link.get('href'),
                          'type'  : link.get('type', ''),
                          'length': link.get('length', 0)})
        else:
          links.append({'rel'   : 'alternate',
                        'href'  : link.get('href'),
                        'type'  : link.get('type', ''),
                        'length': link.get('length', 0)})
    fe.link(links)

    if 'image' in episode and 'href' in episode['image']:
      image_url = episode['image']['href']
      if image_url.rfind('?') > 0:
        image_url = image_url[:image_url.rfind('?')]
      if image_url[-4:] in ('.jpg', '.png'):
        fe.podcast.itunes_image(image_url)

    try:
      fe.podcast.itunes_duration(episode.get('itunes_duration', ''))
    except ValueError:
      duration = episode.get('itunes_duration', '')
      if duration is not '':
        duration = "%s:%s:%s" % (duration[0:2], duration[3:5], duration[6:8])
        fe.podcast.itunes_duration(duration)

  if feed_format == 'feed_atom':
    return fg.atom_str(pretty=True)
  elif feed_format == 'feed_rss':
    return fg.rss_str(pretty=True)


def build_json_feed(feed_object, feed_entries, publication_dates, options):
  """ From the Feed() and the Episodes(), with help from the publication dates dict
      gotten from parse_frequency(), this function makes the RSS feed.
  """
  feed = json.loads(feed_object.content)

  json_feed = {
    "version": "https://jsonfeed.org/version/1",
    "title": feed.get('title', ''),
    "description": strip_tags(feed['summary']) if 'summary' in feed and feed['summary'] != ''
              else strip_tags(feed['description']) if 'description' in feed and feed['description'] != ''
              else strip_tags(feed['subtitle']) if 'subtitle' in feed and feed['subtitle'] != ''
              else 'This feed was generated by Cast Rewinder on %s' % request.host_url,
    "home_page_url": feed.get('link', ''),
    "feed_url": request.url,
    "_castrewinder": {
      "generator": "Cast Rewinder & python-feedgen on %s" % request.host_url,
      "language": feed.get('language', ''),
      "copyright": feed.get('rights', ''),
      "original_url": feed_object.url,
      "pubdate": publication_dates['dates'][-1].isoformat()
    },
    "items": []
  }

  if 'image' in feed and 'href' in feed['image']:
    json_feed['icon'] = feed['image']['href']

  if 'author_detail' in feed:
    json_feed['author'] = {
      'name': feed['author_detail'].get('name', ''),
      'url': 'mailto:%s' % feed['author_detail'].get('email', '')}
  elif 'authors' in feed:
    json_feed['author'] = {
      'name': feed['authors'][0].get('name', ''),
      'url': 'mailto:%s' % feed['authors'][0].get('email', '')}

  for index, entry in enumerate(feed_entries):

    episode = json.loads(entry.content)

    item = {
      "title": episode.get('title', ''),
      "id": "castrewinder_%s_%s" % (request.url, episode.get('id', '')),
      "url": episode.get('link', ''),
      "attachments": []
    }

    summary = strip_tags(html = episode.get('summary', ''))

    if 'keep_dates' in options and options['keep_dates'] == 'yes':

      item['date_published'] = parser.parse(episode.get('published')).isoformat()

      for content in episode.get('content', []):
        if content.get('type') == 'text/plain':
          item['content_text'] = strip_tags(content.get('value'))
        elif content.get('type') == 'text/html':
          item['content_html'] = content.get('value')

    else:
      item['date_published'] = publication_dates['dates'][index].isoformat()
      if 'published_parsed' in episode and episode['published_parsed'] != None:
        episode_published = '-'.join((str(episode['published_parsed'][0]),  # year
                                     str(episode['published_parsed'][1]).zfill(2),  # month
                                     str(episode['published_parsed'][2]).zfill(2))) # day
        summary = "Originally published on %s\n%s" % (episode_published, summary)

      for content in episode.get('content', []):
        if content.get('type') == 'text/plain':
          item['content_text'] = "Originally published on %s.\n%s" % (episode_published, strip_tags(content.get('value')))
        elif content.get('type') == 'text/html':
          item['content_html'] = "<p>Originally published on %s.</p>%s" % (episode_published, content.get('value'))

    item["summary"] = summary
    item["content_text"] = summary


    for media in episode.get('media_content', []):
      item['attachments'].append({
              'url': media.get('url', ''),
              'mime_type': media.get('type', ''),
              'size_in_bytes': media.get('filesize', '')
          })

    for media in episode.get('enclosure', []):
      item['attachments'].append({
              'url': media.get('url', ''),
              'mime_type': media.get('type', ''),
              'size_in_bytes': media.get('filesize', '')
          })

    for link in episode.get('links', []):
      if link.get('rel') == 'enclosure':
        item['attachments'].append({
              'url': link.get('href', ''),
              'mime_type': link.get('type', ''),
              'size_in_bytes': link.get('length', 0)
          })

    if 'image' in episode and episode['image'].get('href'):
      item['image'] = episode['image']['href']

    json_feed['items'].append(item)

  return json.dumps(json_feed)