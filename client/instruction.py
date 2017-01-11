import socket,sys

def send_to_server(data):
    
    f = open ('ServerID','r')
    socketID = f.readline()
    f.close()
    #in the ServerID file, store server IPv file in the formate of 
    #'140.112.5.7:5566' formate
    try:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except socket.error, msg:
        sys.stderr.write('[ERROR] %s\n' % msg[1])
        sys.exit(1)

    try:
        sock.connect((socketID.split(':')[0],socketID.split(':')[1]))
   
    except socket.error, msg:
        sys.stderr.write('[ERROR] %s\n' % msg[1])
        sys.exit(1)

    sock.send(data)
    return sock
    


def recv_from_server(sock):
    dataStr = ''
    while True:
        buff = sock.recv(4096)
        if not buff:
            break
        dataStr = dataStr + buff

    sock.close()
    return(dataStr)



def register(ID,pw):
    ackDict = {'action':'register','from':str(ID) ,'pw':str(pw)}
    sock = send_to_server(json.dumps(ackDict))
    result = json.loads(result(sock))

    print(result['body'],result('time'))
