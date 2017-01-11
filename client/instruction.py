#coding: utf-8
import socket,sys,errno
import json



def new_to_server(data):
    
    f = open ('ServerID','r')
    socketID = f.readline()
    f.close()
    #in the ServerID file, store server IPv file in the formate of 
    #'140.112.5.7:5566' formate

    print(data)
#    print(len(data))
#    get_bin = lambda x, n:format(x,'b').zfill(n)
    matadata = format(len(data.encode('utf-8')),'d').zfill(256)
    print(matadata.encode('utf-8'))
    
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


    sock.send(matadata.encode('utf-8'))
    sock.send(data.encode('utf-8'))
    return sock



def recv_and_close(sock):
    dataStr = b''
    dataSize = int(str(sock.recv(256),'utf-8'))

    dataByte = b''
    dataByte = sock.recv(dataSize)

    dataStr = str(dataByte,'utf-8')

    sock.close()
    print(dataByte)
    print(dataStr)
    return(dataStr)



def register(ID,pw):
    ackDict = {'action':'register','from':str(ID) ,'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    result = json.loads(recv_and_close(sock))
    print(result['body'])
    print(result['time'])
