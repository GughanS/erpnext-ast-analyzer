import streamlit as st
import os
import shutil
import subprocess
import time
from src.parser import get_code_chunks
from src.indexer import CodeIndexer
from src.search import CodeSearcher
from src.generator import CodeGenerator

# --- Page Config ---
st.set_page_config(
    page_title="ERPNext Modernizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styles ---
st.markdown("""
<style>
    .reportview-container { margin-top: -2em; }
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stCodeBlock { max-height: 400px; overflow-y: auto; }
</style>
""", unsafe_allow_html=True)

# --- Session State Init ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar: Configuration & Indexing ---
with st.sidebar:
    st.title("Control Panel")
    
    # Environment Check
    if os.path.exists(".env"):
        st.success(".env loaded")
    else:
        st.error(".env missing")

    st.divider()
    
    st.header("Knowledge Base")
    st.info("Feed the AI with your legacy Python code.")
    
    index_path = st.text_input("Folder/File Path:", value="../erpnext/erpnext/controllers")
    
    if st.button("Start Indexing", type="primary"):
        if not os.path.exists(index_path):
            st.error("Path does not exist!")
        else:
            status_box = st.status("Processing...", expanded=True)
            try:
                indexer = CodeIndexer()
                files = []
                
                status_box.write("Scanning directories...")
                if os.path.isfile(index_path):
                    files.append(index_path)
                else:
                    for root, _, fs in os.walk(index_path):
                        for f in fs:
                            if f.endswith(".py"):
                                files.append(os.path.join(root, f))
                
                status_box.write(f"Parsing {len(files)} files...")
                total_chunks = 0
                progress_bar = status_box.progress(0)
                
                for idx, f in enumerate(files):
                    chunks = get_code_chunks(f)
                    if chunks:
                        indexer.index_chunks(chunks)
                        total_chunks += len(chunks)
                    progress_bar.progress((idx + 1) / len(files))
                
                status_box.update(label=f"Complete! Indexed {total_chunks} functions.", state="complete", expanded=False)
                st.success(f"Successfully added {total_chunks} chunks to ChromaDB.")
                
            except Exception as e:
                status_box.update(label="Failed", state="error")
                st.error(f"Error: {str(e)}")

# --- Main Interface ---
st.title("ERPNext Legacy Modernizer")
st.markdown("Transform your legacy **Python** monolith into modern **Go** microservices.")

# Tabs
tab_chat, tab_migrate, tab_debug = st.tabs(["Ask & Plan", "Migrate & Heal", "Debug Search"])

# --- TAB 1: Chat Interface ---
with tab_chat:
    st.subheader("Context-Aware Assistant")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ex: How does Stock Ledger validation work?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing codebase..."):
                try:
                    searcher = CodeSearcher()
                    results = searcher.search(prompt, limit=5)
                    
                    generator = CodeGenerator()
                    # Check for explain_logic vs answer method availability
                    if hasattr(generator, 'explain_logic'):
                        docs = results.get('documents', [[]])[0]
                        response = generator.explain_logic(prompt, docs)
                    else:
                        response = generator.answer(prompt, results)
                    
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    with st.expander("Referenced Context"):
                        metas = results['metadatas'][0]
                        for m in metas:
                            st.caption(f"`{m['filepath']}` (Line {m['line']})")
                            
                except Exception as e:
                    st.error(f"Error: {e}")

# --- TAB 2: Migration & Self-Healing ---
with tab_migrate:
    st.subheader("Auto-Migration with Compiler Feedback")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        file_path_input = st.text_input("Python File Path", 
                                      placeholder="D:/.../erpnext/stock/doctype/bin/bin.py")
    with col2:
        st.write("")
        st.write("")
        migrate_btn = st.button("Start Migration", type="primary", use_container_width=True)

    if migrate_btn and file_path_input:
        if not os.path.exists(file_path_input):
            st.error(f"File not found: {file_path_input}")
        else:
            # Create a live status container
            status = st.status("Generating Initial Go Implementation...", expanded=True)
            report_logs = []
            
            def log(msg):
                report_logs.append(f"- {msg}")
                # Optional: print to console for debugging
                print(msg)

            try:
                log(f"Started migration for {os.path.basename(file_path_input)}")
                generator = CodeGenerator()
                
                # 1. Initial Generation
                filename_no_ext = os.path.splitext(os.path.basename(file_path_input))[0]
                target_dir = os.path.join("migrated", filename_no_ext)
                
                go_code, test_code = generator.migrate_full_file(file_path_input)
                
                if "GENERATION FAILED" in go_code:
                    status.update(label="AI Generation Failed", state="error")
                    st.error("The AI could not generate the code. Please check your API keys or try again.")
                    log("Migration failed: AI Generation Error")
                    st.stop()

                # Setup Directory
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)
                
                go_file = os.path.join(target_dir, f"{filename_no_ext}.go")
                test_file = os.path.join(target_dir, f"{filename_no_ext}_test.go")
                report_file = os.path.join(target_dir, "migration_report.md")

                def save_files(g, t):
                    with open(go_file, "w", encoding="utf-8") as f: f.write(g)
                    with open(test_file, "w", encoding="utf-8") as f: f.write(t)

                save_files(go_code, test_code)
                status.write("Files saved locally.")
                log("Initial code generated and saved.")

                # Init Module
                status.write("Initializing Go Module...")
                subprocess.run(["go", "mod", "init", filename_no_ext], cwd=target_dir, capture_output=True, check=False)
                subprocess.run(["go", "mod", "tidy"], cwd=target_dir, capture_output=True, check=False)

                # 2. Validation & Healing Loop
                MAX_RETRIES = 3
                success = False
                final_output = ""

                for attempt in range(MAX_RETRIES):
                    status.write(f"Round {attempt + 1}: Running `go test`...")
                    log(f"Verification Round {attempt + 1} started.")
                    
                    process = subprocess.run(["go", "test", "-v"], cwd=target_dir, text=True, capture_output=True)
                    output_log = process.stdout + process.stderr
                    
                    if process.returncode == 0:
                        status.write("Tests Passed!")
                        log(f"Round {attempt + 1}: SUCCESS. All tests passed.")
                        final_output = output_log
                        success = True
                        break
                    
                    status.write(f"Round {attempt + 1} Failed. Analyzing Compiler Errors...")
                    log(f"Round {attempt + 1}: FAILED. Errors detected.")
                    
                    # Heuristic for build errors
                    is_build_error = any(msg in output_log for msg in [
                        "imported and not used", "declared and not used", 
                        "undefined", "expected declaration", "cannot find package",
                        "mock: Unexpected Method Call", "expected 'package'",
                        "syntax error"
                    ])
                    
                    if is_build_error and attempt < MAX_RETRIES - 1:
                        status.write("Applying Self-Healing Fixes...")
                        log(f"Attempting self-healing for Round {attempt + 1} errors.")
                        
                        if f"{filename_no_ext}_test.go" in output_log:
                            test_code = generator.fix_code(test_code, output_log)
                            log("Applied fixes to Test file.")
                        else:
                            go_code = generator.fix_code(go_code, output_log)
                            log("Applied fixes to Implementation file.")
                        
                        save_files(go_code, test_code)
                        # Re-tidy
                        subprocess.run(["go", "mod", "tidy"], cwd=target_dir, capture_output=True, check=False)
                    else:
                        final_output = output_log
                        log("Max retries reached or error not fixable.")
                        break

                # Generate Report
                report_content = f"""# Migration Report: {filename_no_ext}
**Status:** {'SUCCESS' if success else 'FAILED'}
**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}

## Migration Log
{chr(10).join(report_logs)}

## Final Test Output
```text
{final_output}
```
"""
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(report_content)

                if success:
                    status.update(label="Migration Complete & Verified!", state="complete", expanded=False)
                    st.success(f"Migration Successful! Files saved to `migrated/{filename_no_ext}`")
                else:
                    status.update(label="Migration Completed with Errors", state="error", expanded=False)
                    st.warning("Tests failed. Please review the output below.")

                # Results Display
                st.divider()
                st.subheader("Migration Artifacts")
                
                # Report Download
                st.download_button("Download Full Report (.md)", report_content, file_name="migration_report.md")

                with st.expander("View Console Output", expanded=not success):
                    st.code(final_output, language="text")

                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Implementation")
                    st.code(go_code, language="go")
                    st.download_button("Download .go", go_code, file_name=f"{filename_no_ext}.go")
                
                with c2:
                    st.subheader("Test Suite")
                    st.code(test_code, language="go")
                    st.download_button("Download _test.go", test_code, file_name=f"{filename_no_ext}_test.go")

            except Exception as e:
                status.update(label="Critical Error", state="error")
                st.error(f"System Error: {str(e)}")

# --- TAB 3: Debug Search ---
with tab_debug:
    st.subheader("Inspect Vector Database")
    
    search_query = st.text_input("Debug Query", "update stock")
    
    if search_query:
        searcher = CodeSearcher()
        results = searcher.search(search_query, limit=5)
        
        if results and results.get('ids') and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                meta = results['metadatas'][0][i]
                doc = results['documents'][0][i]
                
                with st.expander(f"Result {i+1}: {meta.get('filepath', 'Unknown')} (L{meta.get('line', '?')})"):
                    st.code(doc, language="python")
        else:
            st.warning("No results found.")