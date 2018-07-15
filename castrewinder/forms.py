from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, RadioField
from wtforms.fields.html5 import IntegerField, DateField
from wtforms.widgets.html5 import NumberInput, DateInput
from wtforms.validators import DataRequired
from flask_babel import lazy_gettext

import datetime

import pytz

def generate_timezone_list():
  tz_list = []
  for tz in pytz.common_timezones:
    tz_prettyName = tz.replace('_', ' ')
    tz_diff_from_UTC = datetime.datetime.now(pytz.timezone(tz)).utcoffset().total_seconds()
    tz_sign = '+' if tz_diff_from_UTC > 0 else '-'
    tz_h, tz_m = divmod(abs(tz_diff_from_UTC) / 60, 60)
    tz_UTCOffset = "%02d:%02d" % (tz_h, tz_m)
    tz_list.append((tz, "UTC" + tz_sign + tz_UTCOffset + " - " + tz_prettyName, tz_diff_from_UTC))
  tz_list = sorted(tz_list, key=lambda tz: tz[2])

  return [(value[0], value[1]) for value in tz_list]


class UrlForm(FlaskForm):
  url       = StringField(lazy_gettext('Feed address'),
                          validators=[DataRequired()])
  frequency = SelectField(lazy_gettext('Frequency'),
                          choices=[('daily', lazy_gettext('Daily')),
                                   ('weekly', lazy_gettext('Weekly')),
                                   ('monthly', lazy_gettext('Monthly')),
                                   ('custom_days', lazy_gettext('Select week days:'))],
                          default = 'weekly')
  custom_day_mon = BooleanField(lazy_gettext('Monday'))
  custom_day_tue = BooleanField(lazy_gettext('Tuesday'))
  custom_day_wed = BooleanField(lazy_gettext('Wednesday'))
  custom_day_thu = BooleanField(lazy_gettext('Thursday'))
  custom_day_fri = BooleanField(lazy_gettext('Friday'))
  custom_day_sat = BooleanField(lazy_gettext('Saturday'))
  custom_day_sun = BooleanField(lazy_gettext('Sunday'))

  start_date = DateField(lazy_gettext('Start date'),
                         widget = DateInput(),
                         default = datetime.date.today)

  start_date_timezone = SelectField(lazy_gettext('Timezone'),
                                    choices=generate_timezone_list())

  option_limit = IntegerField(lazy_gettext('Start from episode #'),
                              validators = [DataRequired()],
                              widget = NumberInput(min=1),
                              default = 1)
  option_format = RadioField(lazy_gettext('Feed Format'),
                              default = 'feed_rss',
                              choices=[
                                  ('feed_rss',lazy_gettext('RSS')),
                                  ('feed_atom',lazy_gettext('Atom'))])
  option_order = RadioField(lazy_gettext('Order'),
                              default = 'asc',
                              choices=[
                                  ('asc',lazy_gettext('Oldest first')),
                                  ('desc',lazy_gettext('Newest first'))])
