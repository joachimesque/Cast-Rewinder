from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField
from wtforms.validators import DataRequired

class UrlForm(FlaskForm):
  url       = StringField('Feed address',
                          validators=[DataRequired()])
  frequency = SelectField('Frequency',
                          choices=[('daily', 'Daily'),
                                   ('weekly', 'Weekly'),
                                   ('monthly', 'Monthly'),
                                   ('weekdays', 'Weekdays')])
  weekday_mon = BooleanField('Weekday_mon')
  weekday_tue = BooleanField('Weekday_tue')
  weekday_wed = BooleanField('Weekday_wed')
  weekday_thu = BooleanField('Weekday_thu')
  weekday_fri = BooleanField('Weekday_fri')
  weekday_sat = BooleanField('Weekday_sat')
  weekday_sun = BooleanField('Weekday_sun')