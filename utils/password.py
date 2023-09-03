import string
import hashlib
from random import choice

def generate_password():

    length = 12
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(choice(chars) for i in range(length))
    hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()[:7]
    
    index_1 = choice(range(len(hashed_password)))
    index_2 = choice(range(len(hashed_password)))
    
    hashed_password= hashed_password.replace(hashed_password[index_1], hashed_password[index_1].upper()) 
    hashed_password= hashed_password.replace(hashed_password[index_2], hashed_password[index_2].upper()) 

    # especial_char= choice(['!','@','#','$','*'])
    # hashed_password = hashed_password.replace(hashed_password[choice(range(len(hashed_password)))], especial_char) 
    
    return hashed_password