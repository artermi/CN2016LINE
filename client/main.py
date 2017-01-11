

while True:
    ID = input('Type your ID or new to register:')
    Password = input('password')
    
    Result = False
    if ID == 'new' :
        register(ID,Password)
    else:
        Result = login(ID,Password)

    if Result == True:
        break;



