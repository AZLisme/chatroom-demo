# -*- encoding: utf-8 -*-

HOST = '0.0.0.0'
PORT = 5000
DEBUG = True
UPLOAD_FOLDER = 'uploads'

TITLE = "在线聊天室Demo"
WELCOME = "欢迎来到在线聊天室Demo版本，您可以在此畅所欲言"

# 如果设置为None则每次启动都会自动生成一个
SECRET = None

# 保存数据的路径，Debug模式下无法保存数据
SAVE_PATH = 'saves/save.db'

# 聊天记录最少保留时间(s)，最大保留时间为该值的两倍
EXPIRE_RATE = 600
