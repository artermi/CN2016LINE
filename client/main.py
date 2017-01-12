import instruction as inst
import threading,sys

def give_a_lesson():
    print('Type \'[HIST] USER\' to see the chatting history with USER')
    print('Type \'[SMSG] USER: msg\' to send message \'msg\' to user USER')
    print('Type \'[FILE] USER: file1, file2...\' to send files \'file1, file2...\' to user USER')
    print('Type LOGOUT to logout\n')

while True:
    Result = False

    ID = input('Type your ID to log in or type \'new\' to register: ')
    ID = ID.strip()

    while ID == '':
        ID = input('This is invalid ID. Please type again')
        ID = ID.strip()

    if ID == 'new':
        ID = input('Your ID: ')
        ID = ID.strip()

        while ID.strip() == 'new' or ID == '':
            ID = input('This is invalid ID. Please type again')
            ID = ID.strip()

        Password = input('Password: ')
        inst.register(ID,Password)
    else:
        Password = input('Password: ')
        Result = inst.login(ID,Password)

        if Result['login']:
            break;


thread = threading.Thread(target = inst.always_listen_server, args = (Result['socket'],))
thread.start()

while True:
    Idea = input('May I help you??(Type \'TEACH\' to see instruction formate)\n')
    if Idea.strip() == 'TEACH':
        give_a_lesson()

    else:
        Idea = Idea.lstrip()

        if Idea[:6] == '[HIST]':
            if len(Idea.strip().split()) == 1 :
                print('Parden??')
                continue

            inst.history(Idea.strip().split()[1])

        elif Idea[:6] == '[SMSG]':
            cmd = Idea.partition(':')
            print(cmd)

            if cmd[1] != ':' or cmd[0][6:].strip() == '':
                print('Parden??')
                continue

            inst.msg( cmd[0][6:].strip(),cmd[2])

        elif Idea[:6] == '[FILE]':
            cmd = Idea.partition(':')
            if cmd[1] != ':' or cmd[0][6:].strip() == '':
                print('Parden??')
                continue
                
            inst.file( cmd[0][6:].strip(),cmd[2])
        elif Idea.strip() == 'LOGOUT':
            success = inst.logout(Result['socket'])
            if success:
                print('Bye')
                sys.exit(1)
        else:
            print('Parden??')
