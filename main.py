# -*- encoding: utf-8 -*-
import functools
import hashlib
import itertools
import os
import pickle
import time
import uuid
from collections import defaultdict, namedtuple
from os.path import splitext
from typing import BinaryIO

from flask import Flask, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_socketio import SocketIO, disconnect, emit, join_room
from jsonschema import ValidationError, validate
from werkzeug.datastructures import FileStorage

from config import EXPIRE_RATE, SECRET, TITLE, UPLOAD_FOLDER, WELCOME

app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET or str(uuid.uuid4())
app.config['WELCOME'] = WELCOME
app.config['TITLE'] = TITLE
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app)

user_manager = None  # type: UserManager
history_manager = None  # type: ChatHistoryManager
member_manager = None  # type: MemberListManager

msg_schema = {
    "type": "object",
    "properties": {
        "uid": {"type": "string"},
        "nick": {"type": "string"},
        "msg": {"type": "string"},
        "tp": {"type": "string"},
        "ts": {"type": "number"},
        "room": {"type": "string"}
    }
}

JoinNotifyMessage = namedtuple('JoinNotifyMessage', "uid nick room")
LeaveNotifyMessage = namedtuple('LeaveNotifyMessage', "uid nick room")


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
        self.db[username] = dict(
            password=password, nickname=nickname, date=user.date)
        return user

    def load(self, username):
        if username not in self.db:
            return None
        d = self.db[username]
        user = User(username, d['password'], d['nickname'], d['date'])
        return user

    def nickname(self, username):
        if username not in self.db:
            return None
        return self.db[username]['nickname']


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
        return list(itertools.chain(*self.db))


class MemberListManager:
    def __init__(self):
        self.db = defaultdict(lambda: 0)

    def join(self, uid):
        self.db[uid] += 1

    def leave(self, uid):
        self.db[uid] -= 1

    def online(self, uid):
        return self.db[uid] > 0

    def fresh(self, uid):
        return self.db[uid] == 1

    def all(self):
        return self.db.keys()


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


def cal_md5(f):
    """计算文件的MD5值
    
    :type f: BinaryIO
    :param f:
    :rtype: str
    :return: 
    """
    hexi = hashlib.md5(f.read()).hexdigest()  # type: str
    f.seek(0)
    return hexi


@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        data = dict(uid=current_user.username, nick=current_user.nickname)
        emit('init', data)
    else:
        disconnect()


def verify_msg(json):
    global msg_schema
    try:
        validate(json, msg_schema)
    except ValidationError:
        return False
    uid = current_user.get_id()
    if uid != json['uid']:
        return False
    return True


@socketio.on('chat')
def handle_chat(json):
    if not verify_msg(json):
        return
    room = json['room']
    history_manager.append(json)
    emit('chat', json, room=room)


@socketio.on('join')
def handle_join_event(json):
    room = json['room']
    uid = json['uid']
    nick = json['nick']
    if uid:
        member_manager.join(uid)
        join_room(room)
        emit('chat', history_manager.get())
        if member_manager.fresh(uid):
            emit('join_notify', {'uid': uid, 'nick': nick}, room=room)


@socketio.on('sync_list')
def handle_sync_list(json):
    users = member_manager.all()
    emit('sync_list', [dict(uid=user, nick=user_manager.nickname(user)) for user in users])


# @socketio.on('leave')
# def handle_leave(json):
#     room = json['room']
#     leave_room(room)


@socketio.on('disconnect')
def handle_disconnect():
    uid = current_user.get_id()
    member_manager.leave(uid)
    if not member_manager.online(uid):
        emit('leave_notify', {'uid': uid, 'nick': user_manager.load(
            uid).nickname}, room='default')


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


@app.route('/uploads', methods=['POST'])
def uploads_view():
    f = request.files['file']  # type: FileStorage
    if f is None:
        abort(401)
    md5 = cal_md5(f.stream)
    filename = f.filename
    _, ext = splitext(filename)
    ext = ext.lower()
    if ext[1:] not in ('jpg', 'jpeg', 'png', 'gif'):
        abort(402)
    filename = md5 + ext
    f.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return url_for('get_uploads', path=filename)


@app.route('/uploads/<path:path>', methods=['GET'])
def get_uploads(path):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], path)


def load_data():
    from config import SAVE_PATH
    global user_manager, history_manager, member_manager
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
    member_manager = MemberListManager()


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
