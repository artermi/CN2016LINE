#coding: utf-8
import socket,sys,fcntl,errno,termios
import json,array


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


def recv_from_server(sock):
    Bufsize = array.array('i',[0])

    while True:
        fcntl.ioctl(sock,termios.FIONREAD, Bufsize,1)
        bufsize = Bufsize[0]
        if bufsize != 0:
            break
#    print(bufsize)
    dataByte = b''
    dataByte = sock.recv(bufsize)

    dataStr = str(dataByte,'utf-8')
    return dataStr


def recv_and_close(sock):
    dataStr = recv_from_server(sock)
    sock.close()
    print(dataStr)
    return(dataStr)



def register(ID,pw):
    ackDict = {'action':'register','from':str(ID) ,'pw':str(pw)}
    sock = new_to_server(json.dumps(ackDict))
    result = json.loads(recv_and_close(sock))
    print(result['body'])
    print(result['time'])
