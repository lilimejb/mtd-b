import datetime
import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Games(SqlAlchemyBase):
    __tablename__ = 'games'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    played_date = sqlalchemy.Column(sqlalchemy.DateTime)
    players = sqlalchemy.Column(sqlalchemy.String)