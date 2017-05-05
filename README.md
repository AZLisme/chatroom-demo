# 在线多人聊天室Demo

基于[SocketIO](https://socket.io/)与[Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/)搭建，实验性质的聊天软件。
~~用来狙击¥1800每月的黑心某易云信~~

![Demo地址](http://chat.azlis.me)

## 目前已经测试验证完毕的项目

+ 基于WebSocket，可退化至Long pulling的长连接聊天；
+ 基于Flask-Login的用户认证机制；
+ 自定义消息类型；
+ 储存并恢复聊天记录；

## 还需要进一步验证的项目

+ 生产环境中长时间多人聊天的稳定性
+ 部署在Docker内、由Nginx反向代理的可行性
+ 对于各种手机端的支持

## 运行Demo

### 安装依赖

首先安装Python 3+环境，安装PIP包管理软件

安装相关依赖：

```bash
pip install -r requirements.txt
```

### 修改配置

根据自己的需要，修改Demo中Server运行的端口，定义在`config.py`中。


### 运行Demo

```bash
python main.py
```
## FAQ

### 是否需要安装数据库的支持？

目前不用。所有的数据都保存在内存之中。
好处是对于Demo而言，运行起来更加简单轻便。
缺点是~~每次重启程序都会丢失所有的数据~~现在在生产模式下可以保存记录了。
