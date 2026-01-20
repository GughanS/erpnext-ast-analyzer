import os
import chromadb
import requests
from dotenv import load_dotenv

# 🎯 FIX: Use Absolute Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

# Load keys from absolute path
load_dotenv(dotenv_path=ENV_PATH)

class CodeSearcher:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        try:
            self.collection = self.client.get_collection(name="erpnext_code")
        except ValueError:
            print("⚠️ Error: Collection 'erpnext_code' not found in DB.")
            print(f"   Checked Path: {db_path}")
            self.collection = None
            
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def search(self, query, limit=3):
        if not self.collection:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        # 1. Convert user question to vector (HTTP REST)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": query}]},
            "taskType": "RETRIEVAL_QUERY"
        }

        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(f"❌ Google API Error: {response.text}")
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        query_embedding = response.json()['embedding']['values']

        # 2. Search DB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit
        )

        return results