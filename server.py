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
import array, termios
import miku

BUFF_SIZE = 4096
IDpw = dict({}) # the ID-password mapping
IDlist = dict({})   # this is an empty version of IDsocket, used for IDsocket to initialize
IDsocket = dict({}) # the mapping from ID to connecting sockets
HandlingMsg = []    # this record the sockets currently in the handleMsg state

mikuList = dict({})

HOST = ''
PORT = 9487

watching = []   # the input reading list used for select

lock = threading.Lock() # Use lock to lock the socket_fd

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
    global MikuList
    
    if data['from'] in IDpw:    # ID already registered
        ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '此帳號已註冊'}
        ack = json.dumps(ackDict)
        print(ack)
        sock.send(ack.encode('utf-8'))
        return
        
    IDpw[data['from']] = data['pw']
    IDlist[data['from']] = []
    IDsocket[data['from']] = []
    MikuList[data['from']] = []
    
    dumpMembers()   # add new account information into f 'Members'
    
    os.mkdir('storage/' + data['from'])
    with open('storage/' + data['from'] + '/unread', 'a'):
        pass
        
    ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '註冊成功'}
    ack = json.dumps(ackDict)
#    sock.send((format(len(ack.encode('utf-8')),'d').zfill(256)).encode('utf-8'))

    sock.send(ack.encode('utf-8'))

def login(sock, data):
    global IDpw
    global IDsocket
    
    if data['from'] not in IDpw:    # account not existing
        ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
        
    elif IDpw[data['from']] != data['pw']:  # incorrect password
        ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '密碼錯誤'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
        
    IDsocket[data['from']].append(sock)  # add sock into the client's list
    
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
        sock.send(ack.encode('utf-8'))
        return
            
    ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : body}    # send unread messages to client
    ack = json.dumps(ackDict)
    sock.send(ack.encode('utf-8'))

def msg(sock, data):
    global IDsocket
    global HandlingMsg
    global MikuList
    
    dataStr = json.dumps(data)
    
    if data['to'] not in IDsocket:  # account not existing
        if data['to'] == 'miku':
            
            mikuStr = miku.miku_random_msg_str()
            resDict = {'action' : 'msg', 'from' : 'miku', 'to' : data['from'], 'time' : time.time(), 'body' : mikuStr}
            res = json.dumps(resDict)
            print(res)
            sock.send(res.encode('utf-8'))
            sleep(0.1)

            ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送成功'}
            ack = json.dumps(ackDict)
            sock.send(ack.encode('utf-8'))
            return

        ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
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
        sock.send(ack.encode('utf-8'))
        return
        
    success = 0
    
    for client in IDsocket[data['to']]: # send message to receiver's all online clients

        get_client = False
        t_end = time.time() + 3 #timr out in 3sec
        while time.time() < t_end:
            lock.acquire()
            if client.fileno() not in HandlingMsg:
                HandlingMsg.append(client.fileno())
                get_client = True
                lock.release()
                break
            lock.release()

        if not get_client:
            ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送失敗'}
            ack = json.dumps(ackDict)
            sock.send(ack.encode('utf-8'))
            return

        if data['to'] in MikuList and data['from'] in MikuList[data['to']]:
            newBody = miku.miku_str(str(data['body']))
            data['body'] = newBody
            dataStr = json.dumps(data)

        client.send(dataStr.encode('utf-8'))

        resBi = b''
        Bufsize = array.array('i',[0])
        while True:
            fcntl.ioctl(client,termios.FIONREAD, Bufsize,1)
            bufsize = Bufsize[0]
            if bufsize != 0:
                break

        print(bufsize)
        
        client.settimeout(2)
        try:
            resBi = client.recv(bufsize)
            resStr = str(resBi, 'utf-8')
            print('response:'+ resStr)
            res = json.loads(resStr)
            if res['action'] == 'msg' and res['from'] == data['to'] and res['body'] == '已收到訊息':
                success += 1
        except socket.timeout:
            print('%s :訊息傳送失敗' % data['to'])
        client.settimeout(None)

        lock.acquire()
        HandlingMsg.remove(client.fileno())
        lock.release()
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
        
    ackDict = {'action' : 'msg', 'to' : data['from'], 'time' : time.time(), 'body' : '訊息傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack.encode('utf-8'))
    
def fl(sock, data):
    global IDsocket
    global HandlingMsg
    global BUFF_SIZE
    
    dataLen = data['length']
    dataStr = json.dumps(data)

    ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack.encode('utf-8'))
    #tell the 
    


    if data['to'] not in IDsocket:  # account not existing
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
        
    elif IDsocket[data['to']] == []:    # account offline
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '帳號離線中，無法傳送檔案'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
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


    receivedLen = 0
    recvLen = 0

    buff = [] #firstly recv the file
    while receivedLen < dataLen:
        if dataLen - receivedLen < BUFF_SIZE:
            recvLen = dataLen - receivedLen
        else:
            recvLen = BUFF_SIZE
        
        buff.append(sock.recv(recvLen))
        receivedLen += recvLen
        
        print(dataLen,receivedLen)
    
    
        
    success = 0
    
    for client in IDsocket[data['to']]: # send metafile to receiver's all online clients

        get_client = False
        t_end = time.time() + 3 #timr out in 3sec
        while time.time() < t_end:
            lock.acquire()

#            print(data['name'],'wants handling on',client.fileno())
            if client.fileno() not in HandlingMsg:
                HandlingMsg.append(client.fileno())
                get_client = True
                print('Now who get what:',data['name'],client.fileno())
                lock.release()
                break
#            print(data['name'],'not handling on',client.fileno())
            lock.release()

        if not get_client:
            ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送失敗'}
            ack = json.dumps(ackDict)
            sock.send(ack.encode('utf-8'))
            return

        
        client.send(dataStr.encode('utf-8'))
        
        resBi = b''
        Bufsize = array.array('i',[0])
        while True:
            fcntl.ioctl(client,termios.FIONREAD, Bufsize,1)
            bufsize = Bufsize[0]
            if bufsize != 0:
                break

        client.settimeout(5) ##set the file send timeout in 2 second

        try:
            resBi = client.recv(bufsize)
            resStr = str(resBi, 'utf-8')
        except socket.timeout:
            print('connect to %s timeout' % data['to'])
            resStr = '{"action":"fucked"}'
            lock.acquire()
            client.settimeout(None)
            HandlingMsg.remove(client.fileno())
            lock.release()

        res = json.loads(resStr)
        if res['action'] == 'flinfo' and res['from'] == data['to'] and res['body'] == '已收到檔案資訊':
            success += 1
        else:
            print('幹 收得有問題')
            print(resStr)
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
        
#    ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案資訊傳送成功'}
#    ack = json.dumps(ackDict)
#    sock.send(ack.encode('utf-8'))
    
    receivedLen = 0
    recvLen = 0
    
    for bifile in buff: 
         for client in IDsocket[data['to']]:
             client.send(bifile)
    
    success = 0
    
    for client in IDsocket[data['to']]: # receive response from file receiver's all online clients
        resBi = b''
        Bufsize = array.array('i',[0])
        while True:
            fcntl.ioctl(client,termios.FIONREAD, Bufsize,1)
            bufsize = Bufsize[0]
            if bufsize != 0:
                break
        try:
            resBi = client.recv(bufsize)
            resStr = str(resBi, 'utf-8')
        except socket.timeout:
            print('send file to %s timeout' % data['to'])
            resStr = '("action":"timeout"}'

        res = json.loads(resStr)
        if res['action'] == 'flres' and res['from'] == data['to'] and res['body'] == '已收到檔案':
            success += 1

        print(resStr)

        lock.acquire()
        client.settimeout(None)
        HandlingMsg.remove(client.fileno())
        print('finish handling on',client.fileno())
        lock.release()
            
    if success != len(IDsocket[data['to']]):
        ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案傳送失敗'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return

    ackDict = {'action' : 'fl', 'to' : data['from'], 'time' : time.time(), 'body' : '檔案傳送成功'}
    ack = json.dumps(ackDict)
    sock.send(ack.encode('utf-8'))
    
def history(sock, data):
    global IDsocket
    
    if data['to'] not in IDsocket:  # account not existing
        ackDict = {'action' : 'history', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
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
    sock.send(ack.encode('utf-8'))
#    print(ackDict)

def hatsune(sock, data):
    global MikuList
    
    if data['to'] not in MikuList:  # account not existing
        ackDict = {'action' : 'miku', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
        ack = json.dumps(ackDict)
        sock.send(ack.encode('utf-8'))
        return
    
    if data['to'] not in MikuList[data['from']]:
        MikuList[data['from']].append(data['to'])
    else:
        MikuList[data['from']].remove(data['to'])
        
    ackDict = {'action' : 'miku', 'to' : data['from'], 'time' : time.time(), 'body' : 'Miku設定成功'}  # set client as Miku
    ack = json.dumps(ackDict)
    sock.send(ack.encode('utf-8'))

def logout(sock, data):
    global IDsocket 
    IDsocket[data['from']].remove(sock) # remove sock from the client's list
    
    ackDict = {'action' : 'logout', 'to' : data['from'], 'time' : time.time(), 'body' : '登出成功'}
    ack = json.dumps(ackDict)
    print(ack)
    sock.send(ack.encode('utf-8'))

def handleMsg(sock):
    global HandlingMsg
    global watching
    global IDsocket
    global MikuList

    print('Handling:\n',sock)
   
    Bufsize = array.array('i',[0])
    fcntl.ioctl(sock,termios.FIONREAD, Bufsize,1)
    bufsize = Bufsize[0]
    print(bufsize)
    dataBi = b''
    dataBi = sock.recv(bufsize)
    dataStr = str(dataBi,'utf-8')
    print(dataStr)

    if dataStr == '':   # client socket accidentally closed
        print('closing socket:\n', sock)
        for key in IDsocket:
            if sock in IDsocket[key]:
                try:
                    sock.send('{"action":"try"}'.encode('utf-8'))
                except socket.error as e:
                    print(e)
                    IDsocket[key].remove(sock)  # remove sock from the client's list
                except IOError:
                        IDsocket[key].remove(sock)  # remove sock from the client's list
                print(key,sock)
        if sock in watching:
            watching.remove(sock)
        lock.acquire()
        HandlingMsg.remove(sock.fileno())
        lock.release()
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
    elif data['action'] == 'miku':   
        hatsune(sock, data)
    elif data['action'] == 'logout':    
        logout(sock, data)
    else:
        print('寄錯地方')
    lock.acquire()
    HandlingMsg.remove(sock.fileno())
    lock.release()
    print('finish handling')
    
def loadMembers():
    global IDpw
    global IDlist
    global IDsocket
    global MikuList
    
    with open('storage/Members', 'r') as f: # load IDpw and IDlist from file 'Members', line by line; initialize IDsocket
        IDpwStr = f.readline()
        IDpw = json.loads(IDpwStr)
        IDlistStr = f.readline()
        IDlist = json.loads(IDlistStr)
        IDsocket = copy.deepcopy(IDlist)
        MikuList = copy.deepcopy(IDlist)
    
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
                if sock.fileno() == server.fileno():  # new connection set up
                    conn, addr = server.accept()
                    watching.append(conn)
                    print('Connected by', addr)
    
                elif sock.fileno() not in HandlingMsg:   # check if other threads are handling sock
                    lock.acquire()
                    HandlingMsg.append(sock.fileno())
                    lock.release()
                    thread = threading.Thread(target = handleMsg, args = (sock,))
                    thread.start()

        except KeyboardInterrupt:
            print('server shut down')
            break
            
