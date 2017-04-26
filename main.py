# -*- encoding: utf-8 -*-
import functools
import pickle
import time
import uuid
from functools import reduce

from flask import Flask, flash, redirect, render_template, request
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_socketio import SocketIO, disconnect, emit, join_room, leave_room

from config import SECRET, TITLE, WELCOME, EXPIRE_RATE

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET or str(uuid.uuid4())
app.config['WELCOME'] = WELCOME
app.config['TITLE'] = TITLE

login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app)

user_manager = None  # type: UserManager
history_manager = None  # type: ChatHistoryManager


class UserExist(Exception):
    pass


class User:
    db = dict()

    def __init__(self, username, password, nickname, date):
        self.username = username
        self.password = password
        self.nickname = nickname
        self.date = date

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.username


class UserManager:
    def __init__(self, db=None):
        if db:
            self.db = db
        else:
            self.db = dict()

    def create(self, username, password, nickname):
        if username in self.db:
            raise UserExist
        user = User(username, password, nickname, int(time.time()))
        self.db[username] = dict(password=password, nickname=nickname, date=user.date)
        return user

    def load(self, username):
        if username not in self.db:
            return None
        d = self.db[username]
        user = User(username, d['password'], d['nickname'], d['date'])
        return user


class ChatHistoryManager:

    def __init__(self, db=None):
        if db:
            self.db = db
        else:
            self.db = list()
            self.db.append(list())
            self.db.append(list())
            self.expire = int(time.time()) + EXPIRE_RATE

    def append(self, data):
        self.db[-1].append(data)
        now = int(time.time())
        if now > self.expire:
            self.db.pop(0)
            self.db.append(list())
            self.expire = now + EXPIRE_RATE

    def get(self):
        return reduce(lambda x, y: x + y, self.db)


@login_manager.user_loader
def load_user(user_id):
    return user_manager.load(user_id)


def login_required(redirect_to='/login'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                return func(*args, **kwargs)
            else:
                return redirect(redirect_to)

        return wrapper

    return decorator


def anonymous_required(redirect_to='/'):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                return redirect(redirect_to)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        data = dict(uid=current_user.username, nick=current_user.nickname)
        emit('init', data)
    else:
        disconnect()


@socketio.on('chat')
def handle_chat(json):
    room = json['room']
    history_manager.append(json)
    emit('chat', json, room=room)


@socketio.on('join')
def handle_join_event(json):
    room = json['room']
    join_room(room)
    emit('chat', history_manager.get())


@socketio.on('leave')
def handle_leave(json):
    room = json['room']
    leave_room(room)


@app.route('/', methods=['GET'])
@login_required(redirect_to='/login')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
@anonymous_required()
def login_view():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        user = user_manager.load(username)
        if username == '' or password == '':
            flash('用户名密码不能为空')
            return redirect('/login')
        if not user:
            flash('用户不存在')
            return redirect('/login')
        if user.password != password:
            flash('密码不正确')
            return redirect('/login')
        login_user(user)
        return redirect('/')


@app.route('/logout')
@login_required()
def logout_view():
    logout_user()
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
@anonymous_required()
def register_view():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        nickname = request.form.get('nickname')

        if username == '' or password == '' or nickname == '':
            flash("内容不能为空")
            return redirect('/register')

        if password != password2:
            flash("密码不一致")
            return redirect('/register')

        try:
            user = user_manager.create(username, password, nickname)
        except UserExist:
            flash('该用户已经存在')
            return redirect('/register')

        login_user(user)
        return redirect('/')


def load_data():
    from config import SAVE_PATH
    global user_manager, history_manager
    try:
        with open(SAVE_PATH, 'rb') as f:
            data = pickle.load(f)
    except FileNotFoundError:
        data = None
    if isinstance(data, dict):
        user_manager = data.get('user_manager', UserManager())
        history_manager = data.get('history_manager', ChatHistoryManager())
    else:
        user_manager = UserManager()
        history_manager = ChatHistoryManager()


def save_data():
    from config import SAVE_PATH, DEBUG
    if DEBUG:
        # 在Debug模式下无法保存相关记录？为何读取到的都是空值
        return
    global user_manager, history_manager
    data = dict(user_manager=user_manager, history_manager=history_manager)

    with open(SAVE_PATH, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    from config import DEBUG, PORT, HOST

    load_data()
    try:
        socketio.run(app, host=HOST, port=PORT, debug=DEBUG)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        save_data()
