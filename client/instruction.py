#coding: utf-8
import socket,sys,fcntl,errno,termios,os
import json,array
import select
import time
import threading

curID = ''
SayGoodBye = False

def create_connection():
    f = open ('ServerID','r')
    socketID = f.readline()
    f.close()
    #in the ServerID file, store server IPv file in the formate of 
    #'140.112.5.7:5566' formate    
    try:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except socket.error as msg:
        sys.stderr.write('[ERROR] %s\n' % msg[1])
        sys.exit(1)

    try:
        sock.connect((socketID.split(':')[0],int(socketID.split(':')[1])))
   
    except socket.error as msg:
        sys.stderr.write('[ERROR] %s\n' % msg[1])
        sys.exit(1)
    
    return sock

def new_to_server(data):
    sock = create_connection()
    
    #process the data and matadata
    print(data)
    sock.send(data.encode('utf-8'))
    
    return sock

def recv_byte(sock):
    global SayGoodBye
    Bufsize = array.array('i',[0])

    while True:
        fcntl.ioctl(sock,termios.FIONREAD, Bufsize,1)
        bufsize = Bufsize[0]
        if bufsize != 0:
            break
        if SayGoodBye:
            return
#    print(bufsize)
    dataByte = b''
    dataByte = sock.recv(bufsize)
    return dataByte

def recv_from_server(sock):
    dataByte = recv_byte(sock)
    dataStr = str(dataByte,'utf-8')
    return dataStr


def recv_and_close(sock):
    dataStr = recv_from_server(sock)
    sock.close()
    print(dataStr)
    return(dataStr)


def always_listen_server(sock):
    global curID
    global SayGoodBye
    watching = []
    while True:
        recved = recv_from_server(sock)
        if SayGoodBye:
            return
        result = json.loads(recved)
        if result['action'] == 'msg':
            print(result['body'])
            response = json.dumps({'action':'msg','from':str(curID),'body':'已收到訊息'})
            print(response)
            sock.send(response.encode('utf-8'))
        elif result['action'] == 'fl':
            print(result['name'])
            response = json.dumps({'action':'fl','from':str(curID),'body':'已收到檔案資訊'})
            print(response)
            sock.send(response.encode('utf-8'))
            now_size = 0
            while now_size < result['length']:
                fi_rc = recv_byte(sock)
                now_size += 4096
                print(fi_rc)
            response = json.dumps({'action':'fl','from':str(curID),'body':'已收到檔案'})
            print(response)
            sock.send(response.encode('utf-8'))



def history(user): 
    global curID
    ackDict = {'action':'history', 'to':str(user), 'from':str(curID), 'time' : time.time()}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_and_close(sock))
    print(result['body'])

def msg(user,msg):
    global curID
    ackDict = {'action':'msg', 'to':str(user), 'from':str(curID), 'time' : time.time(),'body':str(msg)}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_and_close(sock))
    print(result['body'])

def send_one_file(user,fname):
    global curID
    totalsize = os.path.getsize(fname)

    ackDict = {'action':'fl', 'to':str(user), 'from':str(curID), 'time' : time.time(),'length': totalsize , 'name':fname}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_from_server(sock))

    print(result['body'])
    if result['body'] != '檔案資訊傳送成功':
        return

    now_size = 0
    with open(fname,'rb') as f:
        while now_size < totalsize:
            byte = f.read(4096)
            print('rdout:'+ str(byte))
            sock.send(byte)
            now_size += 4096
    
    file_status = json.loads(recv_and_close(sock))
    print(file_status['body'])

    return

def file(user, fnames):
    global curID
    files = fnames.split(',')

    fthread = []

    for fi in files:
        fthread.append( threading.Thread(target = send_one_file, args = (user,fi.strip(),)) )

    for th in fthread:
        th.start()

    for th in fthread:
        th.join()
    print('Done')


def logout(sock):
    global SayGoodBye
    print('logout')
    SayGoodBye = True
    return True


def register(ID,pw):
    ackDict = {'action':'register','from':str(ID) ,'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    result = json.loads(recv_and_close(sock))
    print(result['body'])
    print(result['time'])

def login(ID,pw):
    global curID
    ackDict = {'action':'login','from':str(ID), 'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    recv_msg = json.loads( recv_from_server(sock) ) 
    print(recv_msg['body'])

    if recv_msg['body'] != '無此帳號' and recv_msg['body'] != '密碼錯誤':
        curID = ID
        return {'login':True, 'socket' : sock}
    else: 
        sock.close()
        return {'login':False}

