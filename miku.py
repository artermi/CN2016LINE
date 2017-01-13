import unicodedata
import random
import json

def strlen(string):
    len = 0
    #print(element)
    for char in string:
        status = unicodedata.east_asian_width(char)
        #print(status)
        if status == 'F' or status == 'W' or status == 'A':
            #print('{0} is full-width.'.format(char))
            len += 2
        elif status == 'H' or status == 'Na' or status == 'N':
            #print('{0} is half-width.'.format(char))
            len += 1
            
    return len

def miku(msg):
    with open('miku', 'r') as f:
        list = f.readlines()
    
    block = ' ' * strlen(list[2].split('\n')[0])
    #print(msg)
    msg_list = msg.split('\n')
    #print(msg_list)
    
    max_line_len = 0
    for i in msg_list:
        tmp = strlen(i)
        if tmp > max_line_len:
            max_line_len = tmp
        
    line_count = 0
    endmsg = False
    endbubble1 = False
    endbubble2 = False
    i = 0
    while i < len(list):
        
        if line_count < 24:
            print(list[i].split('\n')[0])
        elif line_count == 24:
            print(list[i].split('\n')[0],         '              ____' + '_' * max_line_len +                               '_____')
        elif line_count == 25:
            print(list[i].split('\n')[0],         '            ／    ' + ' ' * max_line_len +                               '     ＼')
        elif line_count == 26 and not endmsg:
            for element in msg_list:
                if line_count == 26:
                    print(list[i].split('\n')[0], '          ＜      ' + element + ' ' * (max_line_len - strlen(element)) + '      ｜')
                elif i < len(list):
                    print(list[i].split('\n')[0], '           ｜     ' + element + ' ' * (max_line_len - strlen(element)) + '      ｜')
                else:
                    print(block,                  '           ｜     ' + element + ' ' * (max_line_len - strlen(element)) + '      ｜')
                i += 1
                line_count += 1
            endmsg = True
            i -= 1
        elif line_count > 26 and endmsg and not endbubble1:
            print(list[i].split('\n')[0],         '            ＼    ' + ' ' * max_line_len +                               '     ／')
            endbubble1 = True
        elif line_count > 26 and endmsg and not endbubble2:
            print(list[i].split('\n')[0],         '              ¯¯¯¯' + '¯' * max_line_len +                               '¯¯¯¯¯')
            endbubble2 = True
        elif endbubble1 and endbubble1:
            print(list[i].split('\n')[0])
        line_count += 1
        i += 1
        
    if not endbubble1:
        print(block,                              '            ＼    ' + ' ' * max_line_len +                               '     ／')
        endbubble1 = True
    if not endbubble2:
        print(block,                              '              ¯¯¯¯' + '¯' * max_line_len +                               '¯¯¯¯¯')
        endbubble2 = True
        
def miku_random_msg():
    with open('miku_msg', 'r') as f:
        miku_msg_str = f.readlines()
    
    miku_msg_list = []
    for i in miku_msg_str:
        miku_msg_list.append(json.loads(i))
    print(miku_msg_list)
    miku(random.choice(miku_msg_list))

miku_random_msg()
#miku('嗨，肥宅！\n你沒有妹妹\n(╬ﾟдﾟ)╭∩╮')