import instruction as inst
import threading,sys

def give_a_lesson():
    print('Type \'[hist] USER\' to see the chatting history with USER')
    print('Type \'[smdg] USER: msg\' to send message \'msg\' to user USER')
    print('Type \'[file] USER: file1, file2...\' to send files \'file1, file2...\' to user USER')
    print('Type logout to logout\n')


def main_program():
    while True:
        Result = False

        ID = input('Type your ID to log in, type \'new\' to register or type \'leave\' to leave: ')
        ID = ID.strip()

        while ID == '':
            ID = input('This is invalid input. Please type again')
            ID = ID.strip()

        if ID == 'new':
            ID = input('Your ID: ')
            ID = ID.strip()

            while ID.strip() == 'new' or ID == '' or ID == 'leave':
                ID = input('This is invalid ID. Please type again')
                ID = ID.strip()

            Password = input('Password: ')
            inst.register(ID,Password)
        elif ID == 'leave':
            return True
        else:
            Password = input('Password: ')
            Result = inst.login(ID,Password)

            if Result['login']:
                break;


    thread = threading.Thread(target = inst.always_listen_server, args = (Result['socket'],))
    thread.start()

    while True:
        Idea = input('May I help you??(Type \'teach\' to see instruction formate)\n')
        if Idea.strip() == 'teach':
            give_a_lesson()

        else:
            Idea = Idea.lstrip()

            if Idea[:6] == '[hist]':
                if len(Idea.strip().split()) == 1 :
                    print('Parden??')
                    continue

                inst.history(Idea.strip().split()[1])

            elif Idea[:6] == '[smsg]':
                cmd = Idea.partition(':')
                print(cmd)

                if cmd[1] != ':' or cmd[0][6:].strip() == '':
                    print('Parden??')
                    continue

                inst.msg( cmd[0][6:].strip(),cmd[2])

            elif Idea[:6] == '[file]':
                cmd = Idea.partition(':')
                if cmd[1] != ':' or cmd[0][6:].strip() == '':
                    print('Parden??')
                    continue
                
                inst.file( cmd[0][6:].strip(),cmd[2])
            elif Idea.strip() == 'logout':
                success = inst.logout(Result['socket'])
                if success:
                    thread.join()
                    print('Bye')
                    return False
            else:
                print('Parden??')

while not main_program():
    pass
