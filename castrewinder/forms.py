from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, RadioField
from wtforms.fields.html5 import IntegerField, DateField
from wtforms.widgets.html5 import NumberInput, DateInput
from wtforms.validators import DataRequired

import datetime

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
