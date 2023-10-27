import redis

def set_check_label(user_id, db: redis.Redis):
    return db.set(f'userChecked:{user_id}', 'checked', ex=25*60*60)

def get_check_label(user_id, db: redis.Redis):
    return db.get(f'userChecked:{user_id}')

def set_test_account_cache(user_id, username_test, ex, db: redis.Redis):
    return db.set(f'test_ssh_account:user:{user_id}:username:{username_test}', 1, ex= ex)

def get_test_account_number(user_id, db: redis.Redis):
    resp = db.keys(f'test_ssh_account:user:{user_id}:*')
    if resp:
        return len(resp)
    
    else :
        return 0

def set_last_domain(value, db: redis.Redis):
    return db.set('last_domain', value)

def get_last_domain(db: redis.Redis):
    return db.get('last_domain')

def set_server_number(number: int, db: redis.Redis):
    return db.set('servernumber', number)

def set_server_proccessing(host: str, db: redis.Redis):
    return db.set(f'server_proccessing:{host}', 'true', ex= 30*60)

def get_server_proccessing(host: str, db: redis.Redis):
    return db.get(f'server_proccessing:{host}')

def get_server_number(db: redis.Redis):
    return db.get('servernumber')

