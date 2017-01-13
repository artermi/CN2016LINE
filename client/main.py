import instruction as inst
import threading,sys

def give_a_lesson():
    print('打 \'[hist] USER\' 看你跟 USER 的聊天記錄')
    print('打 \'[smdg] USER: msg\' 把訊息 \'msg\' 寄給 USER')
    print('打 \'[file] USER: file1, file2...\' 把檔案 \'file1, file2...\' 寄給 USER')
    print('打 \'logout\'登出 ~~')


def main_program():
    while True:
        Result = False

        ID = input('打你的ID登入,打 \'new\' 來註冊或者打 \'bye\'離開\n指令: ')
        ID = ID.strip()

        while ID == '':
            ID = input('泥打的東西是無效的 > < 請重新輸入:')
            ID = ID.strip()

        if ID == 'new':

            ID = input('你的 ID: ')
            ID = ID.strip()
            while ID.strip() == 'new' or ID == '' or ID == 'leave':
                ID = input('這個ID不可以啦 > < 請重新輸入:')
                ID = ID.strip()

            Password = input('密碼: ')
            Password.strip()
            while Password == '':
                Password = input('密碼不可以是空白喔~~~ 請重新輸入:')
                Password.strip()

            inst.register(ID,Password)
        elif ID == 'bye':
            print('掰掰~~ 我們下次見~~~')
            return True
        else:
            Password = input('密碼: ')
            Result = inst.login(ID,Password)

            if Result['login']:
                break;


    thread = threading.Thread(target = inst.always_listen_server, args = (Result['socket'],))
    thread.start()

    while True:
        Idea = input('需要我幫忙嗎~~~(打\'teach\'讓我教你怎麼打指令)\n')
        if Idea.strip() == 'teach':
            give_a_lesson()

        else:
            Idea = Idea.lstrip()

            if Idea[:6] == '[hist]':
                if len(Idea.strip().split()) == 1 :
                    print('公三小??')
                    continue

                inst.history(Idea.strip().split()[1])

            elif Idea[:6] == '[smsg]':
                cmd = Idea.partition(':')
#                print(cmd)

                if cmd[1] != ':' or cmd[0][6:].strip() == '':
                    print('公三小??')
                    continue

                inst.msg( cmd[0][6:].strip(),cmd[2])

            elif Idea[:6] == '[file]':
                cmd = Idea.partition(':')
                if cmd[1] != ':' or cmd[0][6:].strip() == '':
                    print('公三小??')
                    continue 
                inst.fl( cmd[0][6:].strip(),cmd[2])

            elif Idea[:6] == '[miku]':
                cmd = Idea
                if cmd[6:].strip() == '':
                    print('公三小??')
                    continue 
                inst.miku( cmd[6:].strip())

            elif Idea.strip() == 'logout':
                success = inst.logout(Result['socket'])
                if success:
                    thread.join()
                    print('掰掰~~ 我會想念你der~~~')
                    return False
            else:
                print('公三小??')

while not main_program():
    pass
