import os
from typing import Any, Dict

class SupabaseConnector:
    def __init__(self):
        from supabase import create_client, Client
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self.client: Client = create_client(self.url, self.key)

    def insert(self, table: str, record: Dict[str, Any]):
        # If record contains a pdf_blob_path, read as bytes and store as pdf_blob
        if 'pdf_blob_path' in record and record['pdf_blob_path']:
            with open(record['pdf_blob_path'], 'rb') as f:
                record['pdf_blob'] = f.read()
            del record['pdf_blob_path']
        return self.client.table(table).insert(record).execute()

    def fetch(self, table: str, query: Dict[str, Any] = None):
        q = self.client.table(table)
        if query:
            for k, v in query.items():
                q = q.eq(k, v)
        return q.select('*').execute()

class MongoDBConnector:
    def __init__(self):
        from pymongo import MongoClient
        self.url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
        self.client = MongoClient(self.url)
        self.db = self.client[os.getenv('MONGODB_DB', 'email_agent')]

    def insert(self, collection: str, record: Dict[str, Any]):
        return self.db[collection].insert_one(record)

    def fetch(self, collection: str, query: Dict[str, Any] = None):
        return list(self.db[collection].find(query or {}))
