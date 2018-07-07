from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, RadioField
from wtforms.fields.html5 import IntegerField
from wtforms.widgets.html5 import NumberInput
from wtforms.validators import DataRequired

class UrlForm(FlaskForm):
  url       = StringField('Feed address',
                          validators=[DataRequired()])
  frequency = SelectField('Frequency',
                          choices=[('daily', 'Daily'),
                                   ('weekly', 'Weekly'),
                                   ('monthly', 'Monthly'),
                                   ('weekdays', 'Weekdays')])
  weekday_mon = BooleanField('Monday')
  weekday_tue = BooleanField('Tuesday')
  weekday_wed = BooleanField('Wednesday')
  weekday_thu = BooleanField('Thursday')
  weekday_fri = BooleanField('Friday')
  weekday_sat = BooleanField('Saturday')
  weekday_sun = BooleanField('Sunday')

  option_limit = IntegerField('Start from episode #',
                              validators = [DataRequired()],
                              widget = NumberInput(min=1),
                              default = 1)
  option_format = RadioField('Feed Format',
                              default = 'feed_rss',
                              choices=[
                                  ('feed_rss','RSS'),
                                  ('feed_atom','Atom')])