import instruction as inst

while True:
    Result = False

    ID = input('Type your ID to log in or type \'new\' to register:')
    ID = ID.strip()
    if ID == 'new':
        ID = input('Your ID:')
        Password = input('Password:')
        inst.register(ID,Password)
    else:
        Password = input('Password:')
        Result = inst.login(ID,Password)

    if Result == True:
        break;



