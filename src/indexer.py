import os
import chromadb
import requests 
from dotenv import load_dotenv

# 🎯 FIX: Use Absolute Paths so it works from ANY terminal location
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

# Load keys
load_dotenv(dotenv_path=ENV_PATH)

class CodeIndexer:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="erpnext_code")
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def _get_embedding(self, text):
        """
        Uses Google's REST API (HTTP) to bypass gRPC firewall issues.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        
        payload = {
            "model": "models/text-embedding-004",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        }

        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"Google API Error: {response.text}")
            
        # Extract the vector
        return response.json()['embedding']['values']

    def index_chunks(self, chunks):
        """
        Takes a list of code chunks and saves them to the Vector DB
        """
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        print(f"Generating embeddings for {len(chunks)} functions (via HTTP)...")

        for i, chunk in enumerate(chunks):
            # Unique ID with line number
            unique_id = f"{chunk['filepath']}:{chunk['name']}:{chunk['start_line']}"
            
            # Get the vector representation
            try:
                vector = self._get_embedding(chunk['content'])
                
                ids.append(unique_id)
                documents.append(chunk['content'])
                embeddings.append(vector)
                metadatas.append({
                    "name": chunk['name'],
                    "filepath": chunk['filepath'],
                    "line": chunk['start_line']
                })
            except Exception as e:
                print(f"❌ Failed to embed {chunk['name']}: {e}")

        # Save to Database
        if ids:
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            print(f"✅ Successfully indexed {len(ids)} functions!")