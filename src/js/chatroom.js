/**
 * Created by azlisme on 2017/5/4.
 */

function sendMessage() {
    let form = $('textarea.mdl-textfield__input')[0];
    let msg = form.value.trim();
    form.value = "";
    if (msg === "") {
        showToastBar("输入消息不能为空");
        return;
    }
    socket.emit('chat', {uid: uid, nick: nick, msg: msg, ts: +new Date(), room: 'default', tp: 'text'});
}

function sendImage() {
    let blobFile = $('#filechooser')[0].files;
    let formData = new FormData();
    formData.append("file", blobFile[0]);

    $.ajax({
        url: "uploads",
        type: "POST",
        data: formData,
        processData: false,
        contentType: false,
        success: function (response) {
            socket.emit('chat', {
                uid: uid,
                nick: nick,
                msg: response,
                ts: +new Date(),
                room: 'default',
                tp: 'image'
            })
        },
        error: function (jqXHR, textStatus, errorMessage) {
            console.log(errorMessage); // Optional
        }
    });
}

function fadeInNode(node) {
    node.style.marginTop = "64px";
    $(node).animate({
        opacity: '1',
        marginTop: "0"
    }, 'fast', "swing");
}

function appendMessage(_uid, _nick, msg) {
    let list = $('ul.mdl-list')[0];
    let node = document.createElement('li');
    node.innerHTML = `<div class="message with_tail"><div class="username"><b>${_nick}</b></div><div class="content"><div class="text-box">${msg}</div></div></div>`;
    node.style.opacity = "0";
    if (_uid === uid) {
        node.className = 'from-self clearfix';
    } else {
        node.className = 'from-other clearfix';
    }
    list.appendChild(node);
    fadeInNode(node);
}

function clearMessage() {
    let list = $('ul.mdl-list')[0];
    list.innerHTML = '';
}

function appendImage(_uid, _nick, url) {
    let list = $('ul.mdl-list')[0];
    let node = document.createElement('li');
    node.innerHTML = `<div class="message"><div class="username"><b>${_nick}</b></div><div class="content"><img src="${url}"></div></div>`;
    node.opacity = 0;
    if (_uid === uid) {
        node.className = 'from-self clearfix';
    } else {
        node.className = 'from-other clearfix';
    }
    list.appendChild(node);
    fadeInNode(node);
}

function appendMemberList(_uid, _nick) {
    let list = $('ul#member-list')[0];
    let node = document.createElement('li');
    node.innerHTML = `<div class="online-green-light"></div> ${_nick} <span class="id">#${_uid}<span>`;
    node.id = _uid;
    list.appendChild(node);
}

function removeMemberList(_uid) {
    let list = $('ul#member-list')[0];
    let node = list.querySelector(`#${_uid}`);
    if (node !== undefined) {
        list.removeChild(node);
    }
}

function clearMemeberList() {
    let list = $('ul#member-list')[0];
    list.innerHTML = '';
}

function appendSystemMessage(msg) {
    let list = $('ul.mdl-list')[0];
    let node = document.createElement('li');
    node.innerHTML = `<div class="message"><div class="content"><span>${msg}</span></div></div>`;
    node.className = 'system-msg clearfix';
    list.appendChild(node);
}

function handleMessage(data) {
    let _uid = data['uid'];
    let _msg = data['msg'];
    let _nick = data['nick'];
    let _tp = data['tp'];
    switch (_tp) {
        case "text":
            appendMessage(_uid, _nick, escapeHtml(_msg));
            break;
        case "image":
            appendImage(_uid, _nick, _msg);
    }
}

function escapeHtml(text) {
    'use strict';
    return text.replace(/["&'\/<>]/g, function (a) {
        return {
            '"': '&quot;', '&': '&amp;', "'": '&#39;',
            '/': '&#47;', '<': '&lt;', '>': '&gt;'
        }[a];
    });
}
let uid = undefined;
let nick = undefined;
let socket = io.connect('http://' + document.domain + ':' + location.port);
let new_msg = false;

socket.on('init', function (data) {
    uid = data['uid'];
    nick = data['nick'];
    $("#username")[0].innerHTML = uid;
    socket.emit('join', {uid: uid, nick: nick, room: 'default'});
    socket.emit('sync_list', {});
});

socket.on('chat', function (data) {

    if (data instanceof Array) {
        for (let i = 0; i < data.length; i++) {
            handleMessage(data[i])
        }
    } else {
        handleMessage(data)
    }

    let main = $('main');
    main.animate(
        {scrollTop: main[0].scrollHeight - main[0].clientHeight}
    );

    if (document.visibilityState === 'hidden' && new_msg === false) {
        new_msg = true;
        showFlashTitle(document.title);
    }

});

socket.on('join_notify', function (data) {
    let _nick = data['nick'];
    let _uid = data['uid'];
    if (uid === _uid) {
        return;
    }
    appendSystemMessage(`${_nick} 加入了房间`);
    appendMemberList(_uid, _nick)
});

socket.on('leave_notify', function (data) {
    let _nick = data['nick'];
    let _uid = data['uid'];
    appendSystemMessage(`${_nick} 离开了房间`);
    removeMemberList(_uid);
});

socket.on('sync_list', function (data) {
    clearMemeberList();
    for (let i = 0; i < data.length; i++) {
        let element = data[i];
        appendMemberList(element.uid, element.nick);
    }
});

$("#send-button").on('click', sendMessage);
$("#insert_photo_button").on('click', function () {
    $('#filechooser').trigger('click');
});
$('#filechooser').on('change', sendImage);

$("textarea.mdl-textfield__input").keyup(function (event) {
    if (event.keyCode == 13) {
        sendMessage();
    }
});

function showFlashTitle(title, index=0) {
    var prefix = ['【新消息】', '【　　　】']
    document.title = prefix[index] + title;
    if(index === 0) {
        index = 1;
    } else {
        index = 0;
    }
    if(new_msg){
        setTimeout(function () {
            showFlashTitle(title, index);
        }, 500);
    } else {
        document.title = title;
    }
}
document.addEventListener("webkitvisibilitychange", function () {
    if (document.visibilityState === 'visible') {
        new_msg = false;
    };
}, false);
