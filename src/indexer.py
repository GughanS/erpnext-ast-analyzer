import os
import time
import chromadb
import requests
import concurrent.futures
from dotenv import load_dotenv
from src.generator import CodeGenerator

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "chroma_db")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(dotenv_path=ENV_PATH)

class CodeIndexer:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="erpnext_code")
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.generator = CodeGenerator()

    def _get_embedding(self, text):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={self.api_key}"
        payload = {"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}, "taskType": "RETRIEVAL_DOCUMENT"}
        
        # Retry loop for 429 errors
        for attempt in range(3):
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()['embedding']['values']
            elif response.status_code == 429:
                wait = (attempt + 1) * 5
                print(f"Embedding Rate Limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise Exception(f"Google API Error: {response.text}")
        
        return None

    def _process_single_chunk(self, chunk, auto_migrate):
        unique_id = f"{chunk['filepath']}:{chunk['name']}:{chunk['start_line']}"
        result = None

        try:
            # 1. Embed (Index)
            vector = self._get_embedding(chunk['content'])
            if not vector: return None

            result = {
                "id": unique_id,
                "document": chunk['content'],
                "embedding": vector,
                "metadata": {
                    "name": chunk['name'],
                    "filepath": chunk['filepath'],
                    "line": chunk['start_line']
                }
            }

            # 2. Migrate (Generate Go) - OPTIONAL
            if auto_migrate:
                # Add delay to prevent hitting GenAI limits too fast
                time.sleep(2) 
                print(f"   ⚡ Migrating '{chunk['name']}'...")
                self.generator.migrate_and_save(chunk)

        except Exception as e:
            print(f"Failed to process {chunk['name']}: {e}")
        
        return result

    def index_chunks(self, chunks, auto_migrate=False):
        ids, documents, embeddings, metadatas = [], [], [], []

        # REDUCED CONCURRENCY: 3 workers is safer for free tier
        MAX_WORKERS = 3 
        
        print(f"Processing {len(chunks)} functions with {MAX_WORKERS} threads (Rate Limited)...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_chunk = {
                executor.submit(self._process_single_chunk, chunk, auto_migrate): chunk 
                for chunk in chunks
            }
            
            for future in concurrent.futures.as_completed(future_to_chunk):
                result = future.result()
                if result:
                    ids.append(result["id"])
                    documents.append(result["document"])
                    embeddings.append(result["embedding"])
                    metadatas.append(result["metadata"])

        if ids:
            self.collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)
            print(f"Successfully indexed {len(ids)} functions!")