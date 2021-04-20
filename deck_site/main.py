from flask import Flask, render_template, redirect, request, abort
from data import db_session, deck_api
from data.users import User
from data.decks import Decks
from forms.user import RegisterForm, LoginForm
from forms.deck import DecksForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_restful import Api

db_session.global_init("db/mtd_decks.db")

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.confirm_password.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.login == form.login.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        if db_sess.query(User).filter(User.username == form.username.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Не подходящее имя пользователя")
        user = User(
            login=form.login.data,
            username=form.username.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == form.login.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/decks', methods=['GET', 'POST'])
@login_required
def add_deck():
    form = DecksForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        decks = Decks()
        decks.name = form.name.data
        decks.main_deck = form.main_deck.data
        decks.side_board = form.sideboard.data
        current_user.decks.append(decks)
        db_sess.merge(current_user)
        db_sess.commit()
        return redirect('/')
    return render_template('decks.html', title='Добавление колоды',
                           form=form)


@app.route('/decks/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_deck(id):
    form = DecksForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        decks = db_sess.query(Decks).filter(Decks.id == id,
                                            Decks.user == current_user
                                            ).first()
        if decks:
            form.name.data = decks.name
            form.main_deck.data = decks.main_deck
            form.sideboard.data = decks.side_board
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        decks = db_sess.query(Decks).filter(Decks.id == id,
                                            Decks.user == current_user
                                            ).first()
        if decks:
            decks.name = form.name.data
            decks.main_deck = form.main_deck.data
            decks.side_board = form.sideboard.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('decks.html',
                           title='Редактирование колоды',
                           form=form
                           )


@app.route('/')
def start():
    if current_user.is_authenticated:
        return redirect('/login')
    return redirect('/decks')


def main():
    db_session.global_init("db/mtd_decks.db")
    api.add_resource(deck_api.DeckResource, '/api/deck/<int:deck_id>')
    app.run()


if __name__ == '__main__':
    main()
