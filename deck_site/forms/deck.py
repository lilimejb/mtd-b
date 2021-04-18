from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField
from wtforms import BooleanField, SubmitField
from wtforms.validators import DataRequired


class DecksForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired()])
    main_deck = TextAreaField("Main Deck")
    sideboard = TextAreaField("Sideboard")
    submit = SubmitField('Применить')