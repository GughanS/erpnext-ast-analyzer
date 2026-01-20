import click
import os
import sys
from src.parser import get_code_chunks
from src.indexer import CodeIndexer
from src.search import CodeSearcher
from src.generator import CodeGenerator

@click.group()
def cli():
    """ERPNext Code Intelligence Tool"""
    pass

@cli.command()
@click.argument('path', type=click.Path(exists=True))
def index(path):
    """
    Index a file OR a directory recursively.
    """
    indexer = CodeIndexer()
    files_to_process = []

    # 1. Determine if input is file or directory
    if os.path.isfile(path):
        files_to_process.append(path)
    else:
        print(f"📂 Scanning directory: {path}")
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    files_to_process.append(os.path.join(root, file))

    # 2. Process files
    print(f"🚀 Found {len(files_to_process)} Python files to index.")
    
    total_chunks = 0
    for file_path in files_to_process:
        try:
            chunks = get_code_chunks(file_path)
            if chunks:
                indexer.index_chunks(chunks)
                total_chunks += len(chunks)
        except Exception as e:
            print(f"⚠️ Skipping {file_path}: {e}")

    print(f"\n✅ Indexing Complete! {total_chunks} functions stored.")

@cli.command()
@click.argument('query')
def ask(query):
    """Ask AI to explain code logic."""
    print(f"🤔 Asking Groq about: '{query}'...")
    searcher = CodeSearcher()
    results = searcher.search(query, limit=3)
    
    generator = CodeGenerator()
    answer = generator.answer(query, results, mode="explain")
    
    print("\n🤖 Groq Analysis:\n")
    print(answer)
    sys.stdout.flush()

@cli.command()
@click.argument('query')
def migrate(query):
    """Generate Go code based on Python logic."""
    print(f"🏗️ Generating Go code for: '{query}'...")
    searcher = CodeSearcher()
    # Fetch more context (5 chunks) for migration to ensure dependencies are seen
    results = searcher.search(query, limit=5)
    
    generator = CodeGenerator()
    go_code = generator.answer(query, results, mode="migrate")
    
    print("\n📦 Generated Go Code:\n")
    print(go_code)
    sys.stdout.flush()

if __name__ == '__main__':
    cli()