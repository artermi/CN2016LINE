import socket
import select
import threading
import json
import time
import os

BUFF_SIZE = 4096
IDpw = dict({})
IDsocket = dict({})
HandlingMsg = []


HOST = ''
PORT = 5566

watching = []

def	login(sock, data):
	if data['from'] not in IDpw:
		ack = ['action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號']
		sock.send(ack)
		return
	elif IDpw[data['from']] != data['password']:
		ack = ['action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '密碼錯誤']
		sock.send(ack)
		return
	else:
		ack = ['action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '登入成功']
		sock.send(ack)
		IDsocket[data['from']] = IDsocket[data['from']] + sock
		
		file = open('storage/' + data['from'] + '/unread', 'r')
		if not file:
			msg = ['action' : 'unread', 'to' : data['from'], 'time' : time.time(), 'body' : '無未讀訊息']
			sock.send(msg)
		else:
			while True:
				try:
					fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
					break
				except OSError as e:
					if e.errno != errno.EAGAIN:
						raise
						print("can't immediately lock the file")
					else:
						time.sleep(0.1)
			bodyList = []
			for line in file:
				bodyList = bodyList + line
			file.close()
			os.remove('storage/' + data['from'] + '/unread')
			fcntl.flock(file, fcntl.LOCK_UN)
			
			body = json.dumps(bodyList)
			msg = ['action' : 'unread', 'to' : data['from'], 'time' : time.time(), 'body' : body]
			sock.send(msg)
			

def	handleMsg(sock):
	dataStr = ''
	while True:
		buff = sock.recv(BUFF_SIZE)
		if not buff: break
		dataStr = dataStr + buff
	if dataStr == '':	# client socket closed
		#logout(?)
		watching.remove(sock)
		HandlingMsg.remove(sock)
		return
		
	data = json.loads(dataStr)
	if data['action'] == 'register':
		login(sock, data)
	elif data['action'] == 'login':
		login(sock, data)
	elif data['action'] == 'msg':
		msg(sock, data)
	elif data['action'] == 'file':
		file(sock, data)
	elif data['action'] == 'history':	
		history(sock, data)
	elif data['action'] == 'logout':	
		logout(sock, data)
	HandlingMsg.remove(sock)
	
def	loadMembers():
	with open('storage/Members', 'r') as file:
		for line in file:
			member = line.loads(line)
			ID = member['ID']
			pw = member['password']
			IDpw['ID'] = pw
			IDsocket['ID'] = []
	
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
	loadMembers()
	
	server.bind((HOST, PORT))
	server.listen(1024)
	
	watching = watching + server
	timeout = 1
	
	while True:
		with select.select(watching, [], [], timeout) as rlist, wlist, xlist:
			if [rlist, wlist, xlist] == [[], [], []]:	# timeout
				print('select timeout')
			else:
				for sock in rlist:
					if sock == server:	# new connection set up
						conn, addr = server.accept()
						watching = watching + conn
						print('Connected by', addr)
						
						
					elif sock not in HandlingMsg:
						HandlingMsg = HandlingMsg + sock
						thread = threading.Thread(target = handleMsg, args = (sock,))
						thread.start()
						
						