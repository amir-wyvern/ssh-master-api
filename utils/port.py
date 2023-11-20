available_ports = [11570, 6379, 5984, 27017, 7000, 10580, 1521, 5432] #, 1433, 22590]

def generate_port(username):

    if len(username.split('_')) == 1:
        number = 1
        
    else:
        number = int(username.split('_')[1])
    
    return available_ports[number % len(available_ports)]


