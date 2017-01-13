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
#    print(data)
    sock.send(data.encode('utf-8'))
    
    return sock

def recv_byte(sock):
    global SayGoodBye
    Bufsize = array.array('i',[0])

    while True:
        if SayGoodBye:
#            sock.close()
#            print('rb die')
            return b'0'

        fcntl.ioctl(sock,termios.FIONREAD, Bufsize,1)
        bufsize = Bufsize[0]
        if bufsize > 0:
            break
#    print(bufsize)
    dataByte = b''

    dataByte = sock.recv(bufsize)
    return dataByte

def recv_from_server(sock):
    global SayGoodBye
    if SayGoodBye:
        return '{"action":"bye"}'
    dataByte = recv_byte(sock)
    if SayGoodBye:
#        print('rfv die')
        return '{"action":"bye"}'
    dataStr = str(dataByte,'utf-8')
    return dataStr


def recv_and_close(sock):
    dataStr = recv_from_server(sock)
#    sock.close()
#    print(dataStr)
    return(dataStr)

def process_file_name(fresult):
    name = fresult['name']
    named1 = name.split('\\')
    if len(named1) != 1:
        fresult['name'] = named1[-1]
    named2 = name.split('/')
    if len(named2) != 1:
        fresult['name'] = named2[-1]

def feasible_name(fname):
    if not os.path.isdir('Download'):
        os.mkdir('Download')
    new_path = 'Download/'+fname
    fnum = 1
    while os.path.exists(new_path):
        test_name = fname.partition('.')
        if test_name[1] == '.':
            new_path = 'Download/'+test_name[0]+ '_' + str(fnum) + test_name[1] + test_name[2]
        else:
            new_path = 'Download/'+fname +'_'+str(fnum)
        fnum = fnum +1

    return new_path
    


def recv_and_create_file(sock,total_size,fname):
    now_size = 0
    fname = feasible_name(fname)
    
    with open(fname,'wb') as f:
        time_end = time.time() + 10
        while now_size < total_size and time.time() < time_end:
            fi_rc = recv_byte(sock)
            f.write(fi_rc)
            now_size += len(fi_rc)
            print(total_size,now_size)
            print(fi_rc,'\n=============================')


    if now_size >= total_size:
        return True
    else:
        return False


def always_listen_server(sock):
    global curID
    global SayGoodBye
    watching = []
    while True:
        recved = recv_from_server(sock)
        result = json.loads(recved)
        if result['action'] == 'msg':
            print(result['from'],'說:',result['body'])
            response = json.dumps({'action':'msg','from':str(curID),'body':'已收到訊息'})
#            print(response)
            sock.send(response.encode('utf-8'))
            print('需要我幫忙嗎~~(打\'teach\'讓我教你怎麼打指令)')
        elif result['action'] == 'fl':
            process_file_name(result)
            print('Recieve file from:',result['from'],' file name:',result['name'])
            reponse = json.dumps({'action':'flinfo','from':str(curID),'body':'已收到檔案資訊'})
#            print(mata)
            sock.send(reponse.encode('utf-8'))
            recv_success = recv_and_create_file(sock,result['length'],result['name'])


#            now_size = 0
#            while now_size < result['length']:
        #        if result['length'] - now_size < 4096:
        #            fi_rc = sock.recv(result['length'] - now_size)
         #       else: 
#                fi_rc = sock.recv(4096)
 #               fi_rc = recv_byte(sock)

  #              now_size += len(fi_rc)
   #             print(result['length'],now_size)
    #            print(fi_rc,'\n=============================')

            if not recv_success:
                response = json.dumps({'action':'flres','from':str(curID),'body':'沒收到檔案'})
                sock.send(response.encode('utf-8'))
                print('檔案沒有收成功 QQ')
                print('需要我幫忙嗎~~(打\'teach\'讓我教你怎麼打指令)')
                continue

            response = json.dumps({'action':'flres','from':str(curID),'body':'已收到檔案'})
            sock.send(response.encode('utf-8'))
            print('需要我幫忙嗎~~(打\'teach\'讓我教你怎麼打指令)')
        elif result['action'] == 'bye':
            print('正在關閉中~~')
            return
        elif result['action'] == 'logout':
            print(result['body'])


def history(user): 
    global curID
    ackDict = {'action':'history', 'to':str(user), 'from':str(curID), 'time' : time.time()}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_and_close(sock))
    print(result['body'])
#    print('需要我幫忙嗎><(打\'teach\'讓我教你怎麼打指令)')

def msg(user,msg):
    global curID
    ackDict = {'action':'msg', 'to':str(user), 'from':str(curID), 'time' : time.time(),'body':str(msg)}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_and_close(sock))
    if result['body'] == '訊息傳送成功':
        print('已讀')

    print(result['body'])
#    print('需要我幫忙嗎><(打\'teach\'讓我教你怎麼打指令)')

def send_one_file(user,fname):
    global curID
    totalsize = os.path.getsize(fname)

    ackDict = {'action':'fl', 'to':str(user), 'from':str(curID), 'time' : time.time(),'length': totalsize , 'name':fname}
    sock = new_to_server( json.dumps(ackDict) ) 
    result = json.loads(recv_from_server(sock))

    if result['body'] != '檔案資訊傳送成功':
        print('寄給',user,'的檔案',fname,':',result['body'])
        return

    now_size = 0
    with open(fname,'rb') as f:
        while now_size < totalsize:
            byte = f.read(4096)
#            print('rdout:'+ str(byte))
            sock.send(byte)
            now_size += 4096
            if now_size >= totalsize:
                now_size = totalsize
            print('檔案 %s 上傳der進度:' %fname ,str('{:.1%}'.format(now_size/totalsize)))
    
    file_status = json.loads(recv_and_close(sock))
    print('寄給',user,'的檔案',fname,':',file_status['body'])

    return

def fl(user, fnames):
    global curID
    files = fnames.split(',')

    fthread = []

    for fi in files:
        fthread.append( threading.Thread(target = send_one_file, args = (user,fi.strip(),)) )

    for th in fthread:
        th.start()

    for th in fthread:
        th.join()
    print('檔案處理結束束><')
#    print('需要我幫忙嗎><(打\'teach\'讓我教你怎麼打指令)')


def logout(sock):
    global SayGoodBye
    global curID
    ackDict = {'action':'logout', 'from':str(curID), 'time' : time.time()}
    sock.send( json.dumps(ackDict).encode('utf-8')) 
#    result = json.loads(recv_from_server(sock))
#    print(result['body'])
    
    SayGoodBye = True

    return True


def register(ID,pw):
    ackDict = {'action':'register','from':str(ID) ,'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    result = json.loads(recv_and_close(sock))
    print(result['body'])
    print(result['time'])

def login(ID,pw):
    global SayGoodBye
    SayGoodBye = False
    global curID
    ackDict = {'action':'login','from':str(ID), 'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    recv_msg = json.loads( recv_from_server(sock) ) 
#    print(recv_msg)
    print(recv_msg['body'])

    if recv_msg['body'] != '無此帳號' and recv_msg['body'] != '密碼錯誤':
        curID = ID
        return {'login':True, 'socket' : sock}
    else: 
#        sock.close()
        return {'login':False}

