import os
import chromadb
import requests # <--- Switched to requests
from dotenv import load_dotenv

load_dotenv()

class CodeSearcher:
    def __init__(self, db_path="./data/chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name="erpnext_code")
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def search(self, query, limit=3):
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