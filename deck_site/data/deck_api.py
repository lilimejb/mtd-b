import flask
from flask import jsonify

from . import db_session
from .decks import Decks
from flask_restful import abort, Resource

blueprint = flask.Blueprint(
    'deck_api',
    __name__,
    template_folder='templates'
)


def abort_if_deck_not_found(deck_id):
    session = db_session.create_session()
    deck = session.query(Decks).get(deck_id)
    if not deck:
        abort(404, message=f"News {deck_id} not found")


class DeckResource(Resource):
    def get(self, deck_id):
        abort_if_deck_not_found(deck_id)
        session = db_session.create_session()
        deck = session.query(Decks).get(deck_id)
        return jsonify({'deck': deck.to_dict(
            only=('name', 'main_deck', 'side_board', 'user_id'))})
