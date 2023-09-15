import redis

def get_auth_code_by_session(token: str, db: redis.Redis):
    return db.get(token)

def set_lock_for_user(user_id, db):
    return db.set(f'lock:user:{user_id}', 'True', ex= 300)

def set_lock_for_tx_hash(tx_hash, db):
    return db.set(f'lock:tx_hash:{tx_hash}', 'True', ex= 300)

def unlock_user(user_id, db):
    return db.delete(f'lock:user:{user_id}')

def unlock_tx_hash(tx_hash, db):
    return db.delete(f'lock:tx_hash:{tx_hash}')

def get_status_lock_from_user(user_id, db: redis.Redis):
    return db.get(f'lock:user:{user_id}')

def get_status_lock_from_tx_hash(tx_hash, db: redis.Redis):
    return db.get(f'lock:tx_hash:{tx_hash}')

def set_check_label(user_id, db: redis.Redis):
    return db.set(f'userChecked:{user_id}', 'checked', ex=24*60*60)

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

