import socket
import select
import threading
import json
import time
import os
import fcntl
import copy
import subprocess
import codecs

BUFF_SIZE = 4096
IDpw = dict({}) # the ID-password mapping
IDlist = dict({})   # this is an empty version of IDsocket, used for IDsocket to initialize
IDsocket = dict({}) # the mapping from ID to connecting sockets
HandlingMsg = []    # this record the sockets currently in the handleMsg state

HOST = ''
PORT = 5566

watching = []   # the input reading list used for select

def dumpMembers():
    global IDpw
    global IDlist
    
    IDpwStr = json.dumps(IDpw)
    IDlistStr = json.dumps(IDlist)
    
    with open('storage/Members', 'w') as f:
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
        
        f.write(IDpwStr + '\n' + IDlistStr + '\n')  # dump IDpw and IDlist into f 'Members', line by line
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock

def register(sock, data):
    global IDpw
    global IDlist
    global IDsocket
    
    if data['from'] in IDpw:    # ID already registered
        ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '此帳號已註冊'}
        ack = json.dumps(ackDict)
        print(ack)
        sock.send((format(len(ack.encode('utf-8')),'d').zfill(256)).encode('utf-8'))
        sock.send(ack.encode('utf-8'))
        return
        
    IDpw[data['from']] = data['pw']
    IDlist[data['from']] = []
    IDsocket[data['from']] = []
    
    dumpMembers()   # add new account information into f 'Members'
    
    os.mkdir('storage/' + data['from'])
    with open('storage/' + data['from'] + '/unread', 'a'):
        pass
        
    ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '註冊成功'}
    ack = json.dumps(ackDict)
    sock.send((format(len(ack.encode('utf-8')),'d').zfill(256)).encode('utf-8'))

    sock.send(ack.encode())

def login(sock, data):
    global IDpw
    global IDsocket
    
    if data['from'] not in IDpw:    # account not existing
        ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    elif IDpw[data['from']] != data['pw']:  # incorrect password
        ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '密碼錯誤'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    IDsocket[data['from']] = IDsocket[data['from']] + sock  # add sock into the client's list
    
    with open('storage/' + data['from'] + '/unread', 'r+') as f:
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
            
        body = f.readlines()
        f.seek(0, 0)
        f.truncate()
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    if body == []:  # file 'unread' is empty
        ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '登入成功，無未讀訊息'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
            
    ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : body}    # send unread messages to client
    ack = json.dumps(ackDict)
    sock.send(ack)

def msg(sock, data):
    global IDsocket
    
    dataStr = json.dumps(data)
    
    if data['to'] not in IDsocket:  # account not existing
        ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    with open('storage/' + data['to'] + '/' + data['from'] + '.log', 'a') as f: # write to log on receiver's side
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
                
        f.write(dataStr + '\n')
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    with open('storage/' + data['from'] + '/' + data['to'] + '.log', 'a') as f: # write to log on sender's side
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
                
        f.write(dataStr + '\n')
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    if IDsocket[data['to']] == []:  # account offline, append message to 'unread'
        
        with open('storage/' + data['to'] + '/unread', 'a') as f:   # write to unread on receiver's side
            while True: # requiring exclusive lock
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    print('Someone is accessing ' + f.name)
                    time.sleep(0.1)
                    
            f.write(dataStr + '\n')
            
            fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
        ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '帳號離線中，已加入未讀訊息'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    success = 0
    
    for client in IDsocket[data['to']]: # send message to receiver's all online clients
        client.send(dataStr)
        
        resStr = ''
        while True:
            buff = client.recv(BUFF_SIZE)
            if not buff:
                break
            resStr = resStr + buff
            
        res = json.loads(resStr)
        if res['action'] == 'msg' and res['from'] == data['to'] and res['body'] == '已收到訊息':
            success += 1
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack)
    
def fl(sock, data):
    global IDsocket
    
    dataLen = data['length']
    dataStr = json.dumps(data)
    
    if data['to'] not in IDsocket:  # account not existing
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    elif IDsocket[data['to']] == []:    # account offline
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '帳號離線中，無法傳送檔案'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    with open('storage/' + data['to'] + '/' + data['from'] + '.log', 'a') as f: # write metafile to log on receiver's side
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
                
        f.write(dataStr + '\n')
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    with open('storage/' + data['from'] + '/' + data['to'] + '.log', 'a') as f: # write metafile to log on sender's side
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
                
        f.write(dataStr + '\n')
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    success = 0
    
    for client in IDsocket[data['to']]: # send metafile to receiver's all online clients
        client.send(dataStr)
        
        resStr = ''
        while True:
            buff = client.recv(BUFF_SIZE)
            if not buff:
                break
            resStr = resStr + buff
            
        res = json.loads(resStr)
        if res['action'] == 'fl' and res['from'] == data['to'] and res['body'] == '已收到檔案資訊':
            success += 1
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
        
    ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack)
    
    receivedLen = 0
    recvLen = 0
    
    while receivedLen < dataLen:    # send file to receiver's all online clients
        if dataLen - receivedLen < BUFF_SIZE:
            recvLen = dataLen - receivedLen
        else:
            recvLen = BUFF_SIZE
        
        buff = sock.recv(recvLen)
        receivedLen += recvLen
        
        for client in IDsocket[data['to']]:
            sock.send(buff)
    
    success = 0
    
    for client in IDsocket[data['to']]: # receive response from file receiver's all online clients
        resStr = ''
        while True:
            buff = client.recv(BUFF_SIZE)
            if not buff:
                break
            resStr = resStr + buff
            
        res = json.loads(resStr)
        if res['action'] == 'fl' and res['from'] == data['to'] and res['body'] == '已收到檔案':
            success += 1
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return

    ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack)
    
def history(sock, data):
    global IDsocket
    
    if data['to'] not in IDsocket:  # account not existing
        ackDict = {'action' : 'history', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack)
        return
    
    with open('storage/' + data['from'] + '/' + data['to'] + '.log', 'r+') as f:
        while True: # requiring exclusive lock
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                print('Someone is accessing ' + f.name)
                time.sleep(0.1)
            
        body = f.readlines()
        
        fcntl.flock(f, fcntl.LOCK_UN)   # release lock
        
    ackDict = {'action' : 'history', 'to' : data['from'], 'time' : time.time(), 'body' : body}  # send log to client
    ack = json.dumps(ackDict)
    sock.send(ack)

def logout(sock, data):
    global IDsocket
    
    IDsocket[data['from']].remove(sock) # remove sock from the client's list
    
    ackDict = {'action' : 'logout', 'to' : data['from'], 'time' : time.time(), 'body' : body}
    ack = json.dumps(ackDict)
    sock.send(ack)

def handleMsg(sock):
    global HandlingMsg
    global watching
    global IDsocket
   
    dataMata = sock.recv(256)
    dataStr = ''
    if dataMata:
        print(dataMata)
        dataSize = int(str(dataMata,'utf-8'))
        print(dataSize)

        dataByte = b''
        dataByte = sock.recv(dataSize)
        dataStr = str(dataByte,'utf-8')

        print(dataStr)
        
    if dataStr == '':   # client socket accidentally closed
        for key in IDsocket:
            if sock in IDsocket[key]:
                IDsocket[key].remove(sock)  # remove sock from the client's list
        watching.remove(sock)
        HandlingMsg.remove(sock)
        return

    data = json.loads(dataStr)
    if data['action'] == 'register':
        register(sock, data)
    elif data['action'] == 'login':
        login(sock, data)
    elif data['action'] == 'msg':
        msg(sock, data)
    elif data['action'] == 'fl':
        fl(sock, data)
    elif data['action'] == 'history':   
        history(sock, data)
    elif data['action'] == 'logout':    
        logout(sock, data)
    HandlingMsg.remove(sock)
    
def loadMembers():
    global IDpw
    global IDlist
    global IDsocket
    
    with open('storage/Members', 'r') as f: # load IDpw and IDlist from file 'Members', line by line; initialize IDsocket
        IDpwStr = f.readline()
        IDpw = json.loads(IDpwStr)
        IDlistStr = f.readline()
        IDlist = json.loads(IDlistStr)
        IDsocket = copy.deepcopy(IDlist)
    
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        loadMembers()
    
        server.bind((HOST, PORT))
        server.listen(1024)
        print(str(socket.gethostbyname(socket.gethostname())+':'+str(PORT)))
    
        watching.append(server)
    
        while True:
                try:
                        rlist, wlist, xlist = select.select(watching, [], [])

                        for sock in rlist:
                                if sock == server:  # new connection set up
                                        conn, addr = server.accept()
                                        watching.append(conn)
                                        print('Connected by', addr)
                    
                                elif sock not in HandlingMsg:   # check if other threads are handling sock
                                        HandlingMsg.append(sock)
                                        thread = threading.Thread(target = handleMsg, args = (sock,))
                                        thread.start()
                except KeyboardInterrupt:
                        print('server shut down')
                        break
                
