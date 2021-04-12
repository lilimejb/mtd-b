from flask_wtf import FlaskForm
from wtforms import SubmitField


class StartForm(FlaskForm):
    submit = SubmitField('Войти')