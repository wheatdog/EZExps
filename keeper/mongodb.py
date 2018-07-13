from .base import Keeper
from pymongo import MongoClient

class MongoKeeper(Keeper):
    def __init__(self, database=''):
        client = MongoClient()
        db = client[database]
        self.collect = db['runs']

    def push(self, data):
        result = self.collect.insert_one(data)
