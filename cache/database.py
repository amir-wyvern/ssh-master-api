import os
from dotenv import load_dotenv
from pathlib import Path
import redis

dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)

CACHE_URL = os.getenv('CACHE_URL')

class RedisSingleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, url):
        if not hasattr(self, '_redis_db'):
            self._redis_db = redis.Redis.from_url(url, decode_responses=True)

    @property
    def redis_db(self):
        return self._redis_db


session = RedisSingleton(CACHE_URL)


def get_redis_cache():
    try:
        yield session.redis_db

    finally:
        session.redis_db.close()

