from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, RadioField
from wtforms.fields.html5 import IntegerField, DateField
from wtforms.widgets.html5 import NumberInput, DateInput
from wtforms.validators import DataRequired

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
  url       = StringField('Feed address',
                          validators=[DataRequired()])
  frequency = SelectField('Frequency',
                          choices=[('daily', 'Daily'),
                                   ('weekly', 'Weekly'),
                                   ('monthly', 'Monthly'),
                                   ('custom_days', 'Select week days:')],
                          default = 'weekly')
  custom_day_mon = BooleanField('Monday')
  custom_day_tue = BooleanField('Tuesday')
  custom_day_wed = BooleanField('Wednesday')
  custom_day_thu = BooleanField('Thursday')
  custom_day_fri = BooleanField('Friday')
  custom_day_sat = BooleanField('Saturday')
  custom_day_sun = BooleanField('Sunday')

  start_date = DateField('Start date',
                         widget = DateInput(),
                         default = datetime.date.today)

  start_date_timezone = SelectField('Timezone',
                                    choices=generate_timezone_list())

  option_limit = IntegerField('Start from episode #',
                              validators = [DataRequired()],
                              widget = NumberInput(min=1),
                              default = 1)
  option_format = RadioField('Feed Format',
                              default = 'feed_rss',
                              choices=[
                                  ('feed_rss','RSS'),
                                  ('feed_atom','Atom')])
  option_order = RadioField('Order',
                              default = 'asc',
                              choices=[
                                  ('asc','Oldest first'),
                                  ('desc','Newest first')])
