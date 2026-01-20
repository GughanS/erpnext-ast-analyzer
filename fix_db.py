import os
from src.parser import get_code_chunks
from src.indexer import CodeIndexer
from colorama import Fore, Style, init

init(autoreset=True)

# The filenames we absolutely need for the QA to pass
TARGET_FILES = ["selling_controller.py", "accounts_controller.py", "stock_ledger.py"]

def find_and_index():
    print(f"{Fore.CYAN}🕵️‍♀️ Hunting for missing controller files...{Style.RESET_ALL}")
    
    # 1. Start searching from the parent directory
    # Adjust this if your erpnext folder is somewhere else
    search_root = ".." 
    found_count = 0
    indexer = CodeIndexer()

    for root, dirs, files in os.walk(search_root):
        for filename in files:
            if filename in TARGET_FILES:
                full_path = os.path.join(root, filename)
                print(f"   found: {full_path}")
                
                # CHECK: Don't re-index if already there
                existing_count = indexer.collection.count(where={"filepath": full_path})
                if existing_count > 0:
                    print(f"   {Fore.CYAN}ℹ️  Skipping {filename} (Already indexed {existing_count} functions){Style.RESET_ALL}")
                    found_count += 1
                    continue
                
                # 2. Index immediately
                try:
                    print(f"   {Fore.YELLOW}Indexing {filename}...{Style.RESET_ALL}")
                    chunks = get_code_chunks(full_path)
                    if chunks:
                        indexer.index_chunks(chunks)
                        print(f"   {Fore.GREEN}✅ Success! Added {len(chunks)} functions.{Style.RESET_ALL}")
                        found_count += 1
                except Exception as e:
                    print(f"   {Fore.RED}❌ Error indexing: {e}{Style.RESET_ALL}")

    if found_count == 0:
        print(f"\n{Fore.RED}❌ Could not find the files on disk!{Style.RESET_ALL}")
        print("Please ensure you have downloaded the 'erpnext' source code folder")
        print("and it is located next to this 'erpnext-ast-analyzer' folder.")
    else:
        print(f"\n{Fore.GREEN}✨ Fixed! {found_count} critical files added to DB.{Style.RESET_ALL}")
        print("Now run 'python qa_benchmark.py' again.")

if __name__ == "__main__":
    find_and_index()