import socket
import select
import threading
import json
import time
import os
import fcntl
import copy

BUFF_SIZE = 4096
IDpw = dict({})	# the ID-password mapping
IDlist = dict({})	# this is an empty version of IDsocket, used for IDsocket to initialize
IDsocket = dict({})	# the mapping from ID to connecting sockets
HandlingMsg = []	# this record the sockets currently in the handleMsg state

HOST = ''
PORT = 5566

watching = []	# the input reading list used for select

def dumpMembers():
	global IDpw
	global IDlist
	
	IDpwStr = json.dump(IDpw)
	IDlistStr = json.dump(IDlist)
	
	with open('storage/Members', 'w') as file:
		while True:	# requiring exclusive lock
			try:
				fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
				break
			except BlockingIOError:
				print('Someone is accessing ' + file.name)
				time.sleep(0.1)
		
		file.write(IDpwStr + '\n' + IDlistStr + '\n')	# dump IDpw and IDlist into file 'Members', line by line
		
		fcntl.flock(file, fcntl.LOCK_UN)	# release lock

def register(sock, data):
	global IDpw
	global IDlist
	global IDsocket
	
	if data['from'] in IDpw:	# ID already registered
		ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '此帳號已註冊'}
		ack = json.dumps(ackDict)
		sock.send(ack)
		
	else:	# register succeeded
		IDpw[data['from']] = data['pw']
		IDlist[data['from']] = []
		IDsocket[data['from']] = []
		
		ackDict = {'action' : 'register', 'to' : data['from'], 'time' : time.time(), 'body' : '註冊成功'}
		ack = json.dumps(ackDict)
		
		dumpMembers()	# add new account information into file 'Members'
		
		os.mkdir('storage/' + data['from'])
		with open('storage/' + data['from'] + '/unread', 'a'):
			pass
		
		sock.send(ack)

def login(sock, data):
	global IDpw
	global IDsocket
	
	if data['from'] not in IDpw:	# account not existing
		ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '無此帳號'}
		ack = json.dumps(ackDict)
		sock.send(ack)
		
	elif IDpw[data['from']] != data['pw']:	# incorrect password
		ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '密碼錯誤'}
		ack = json.dumps(ackDict)
		sock.send(ack)
		
	else:	# login succeeded
		IDsocket[data['from']] = IDsocket[data['from']] + sock	# add sock into the client's list
		
		msg_count = 0
		body = []
		
		with open('storage/' + data['from'] + '/unread', 'r+') as file:
			while True:	# requiring exclusive lock
				try:
					fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
					break
				except BlockingIOError:
					print('Someone is accessing ' + file.name)
					time.sleep(0.1)
					
			for line in file:	# pack all unread message into body
				body.append(line)
				msg_count += 1
			
			file.seek(0, 0)
			file.truncate()
			
			fcntl.flock(file, fcntl.LOCK_UN)	# release lock
			
		if msg_count == 0:	# file 'unread' is empty
			ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : '登入成功，無未讀訊息'}
			ack = json.dumps(ackDict)
			sock.send(ack)
			return
				
		ackDict = {'action' : 'login', 'to' : data['from'], 'time' : time.time(), 'body' : body}	# send unread messages to client
		ack = json.dumps(ackDict)
		sock.send(ack)

def msg(sock, data):
	pass

def file(sock, data):
	pass
	
def history(sock, data):
	pass

def logout(sock, data):
	global IDsocket
	
	if sock in IDsocket[data['from']]:
		IDsocket[data['from']].remove(sock)	# remove sock from the client's list

def handleMsg(sock):
	global HandlingMsg
	global watching
	
	dataStr = ''
	while True:
		buff = sock.recv(BUFF_SIZE)
		if not buff:
			break
		dataStr = dataStr + buff
		
	if dataStr == '':	# client socket closed
		logout(sock, data)
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
	elif data['action'] == 'file':
		file(sock, data)
	elif data['action'] == 'history':	
		history(sock, data)
	elif data['action'] == 'logout':	
		logout(sock, data)
	HandlingMsg.remove(sock)
	
def loadMembers():
	global IDpw
	global IDlist
	global IDsocket
	
	with open('storage/Members', 'r') as file:	# load IDpw and IDlist from file 'Members', line by line; initialize IDsocket
		IDpwStr = file.readline()
		IDpw = json.loads(IDpwStr)
		IDlistStr = file.readline()
		IDlist = json.loads(IDlistStr)
		IDsocket = copy.deepcopy(IDlist)
	
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
	loadMembers()
	
	server.bind((HOST, PORT))
	server.listen(1024)
	
	watching.append(server)
	
	while True:
		try:
			rlist, wlist, xlist = select.select(watching, [], [])

			for sock in rlist:
				if sock == server:	# new connection set up
					conn, addr = server.accept()
					watching.append(conn)
					print('Connected by', addr)
					
				elif sock not in HandlingMsg:	# check if other threads are handling sock
					HandlingMsg.append(sock)
					thread = threading.Thread(target = handleMsg, args = (sock,))
					thread.start()
		except KeyboardInterrupt:
			print('server shut down')
			break
				