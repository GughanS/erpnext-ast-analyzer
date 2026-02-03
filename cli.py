import click
import os
import subprocess
import shutil
import logging
import time
from src.parser import get_code_chunks
from src.indexer import CodeIndexer
from src.search import CodeSearcher
from src.generator import CodeGenerator

# Setup basic logging for CLI
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@click.group()
def cli():
    """ERPNext Code Intelligence & Migration Tool"""
    pass

@click.command()
@click.argument('path', type=click.Path(exists=True))
def index(path):
    """Index a file or folder for search and context-aware queries."""
    indexer = CodeIndexer()
    files = []
    
    # 1. Gather Files
    if os.path.isfile(path):
        if path.endswith(".py"):
            files.append(path)
    else:
        for root, _, fs in os.walk(path):
            for f in fs:
                if f.endswith(".py"):
                    files.append(os.path.join(root, f))
    
    if not files:
        click.echo(click.style(f"No Python files found in {path}", fg="yellow"))
        return

    click.echo(click.style(f"Found {len(files)} files. Starting indexing...", fg="cyan"))
    
    # 2. Process Files with Progress Bar
    with click.progressbar(files, label="Indexing Progress") as bar:
        for f in bar:
            try:
                chunks = get_code_chunks(f)
                if chunks:
                    indexer.index_chunks(chunks)
            except Exception as e:
                logger.error(f"Failed to index {f}: {e}")
                
    click.echo(click.style("Indexing Complete.", fg="green", bold=True))

@click.command()
@click.argument('query')
def ask(query):
    """Query the indexed codebase using RAG."""
    searcher = CodeSearcher()
    try:
        results = searcher.search(query)
        generator = CodeGenerator()
        
        docs = results.get('documents', [[]])[0]
        
        if not docs:
            click.echo(click.style("No relevant context found in index.", fg="yellow"))
            
        answer = generator.explain_logic(query, docs)
            
        click.echo("\n" + click.style("AI Response:", fg="blue", bold=True))
        click.echo(answer)
    except Exception as e:
        click.echo(click.style(f"Error querying index: {e}", fg="red"))

@click.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--out-dir', default='migrated', help='Directory to save migrated code.')
def migrate_file(file_path, out_dir):
    """
    Migrate a Python file to Go + Tests with Self-Healing capabilities.
    """
    generator = CodeGenerator()
    filename_no_ext = os.path.splitext(os.path.basename(file_path))[0]
    target_dir = os.path.join(out_dir, filename_no_ext)
    
    # Track logs for report
    report_logs = []
    def log(msg):
        report_logs.append(f"- {msg}")
    
    # 1. Initial Generation
    click.echo(click.style(f"Generating Go logic for {filename_no_ext}...", fg="cyan"))
    log(f"Started migration for {filename_no_ext}")
    
    go_code, test_code = generator.migrate_full_file(file_path_input=file_path)

    # Prepare Directory
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)
    
    go_file = os.path.join(target_dir, f"{filename_no_ext}.go")
    test_file = os.path.join(target_dir, f"{filename_no_ext}_test.go")
    report_file = os.path.join(target_dir, "migration_report.md")

    def save_files(g_code, t_code):
        with open(go_file, "w", encoding="utf-8") as f: f.write(g_code)
        with open(test_file, "w", encoding="utf-8") as f: f.write(t_code)

    save_files(go_code, test_code)
    log("Initial code generated and saved.")
    
    click.echo(click.style(f"Files saved in: {target_dir}", fg="green"))

    # Initialize Module
    click.echo(click.style("Initializing Go Environment...", fg="yellow"))
    subprocess.run(["go", "mod", "init", filename_no_ext], cwd=target_dir, capture_output=True, check=False)
    subprocess.run(["go", "mod", "tidy"], cwd=target_dir, capture_output=True, check=False)

    # 2. Validation & Self-Healing Loop
    MAX_RETRIES = 3
    success = False
    final_output = ""

    for attempt in range(MAX_RETRIES):
        click.echo(click.style(f"\nVerification Round {attempt + 1}...", fg="yellow"))
        log(f"Verification Round {attempt + 1} started.")
        
        process = subprocess.run(["go", "test", "-v"], cwd=target_dir, text=True, capture_output=True)
        
        if process.returncode == 0:
            click.echo(process.stdout)
            click.echo(click.style("\nSUCCESS: All tests passed!", fg="green", bold=True))
            log(f"Round {attempt + 1}: SUCCESS. All tests passed.")
            final_output = process.stdout + process.stderr
            success = True
            break
        
        # Check for compilation errors
        error_log = process.stderr + process.stdout
        final_output = error_log
        click.echo(click.style(f"Failure detected. Analyzing errors...", fg="red"))
        log(f"Round {attempt + 1}: FAILED. Errors detected.")
        
        is_build_error = any(msg in error_log for msg in [
            "imported and not used", "declared and not used", 
            "undefined", "expected declaration", "cannot find package",
            "mock: Unexpected Method Call", "expected 'package'",
            "syntax error"
        ])
        
        if is_build_error and attempt < MAX_RETRIES - 1:
            click.echo(click.style("Applying Self-Healing Fixes...", fg="magenta"))
            log(f"Attempting self-healing for Round {attempt + 1} errors.")
            
            if f"{filename_no_ext}_test.go" in error_log:
                test_code = generator.fix_code(test_code, error_log)
                log("Applied fixes to Test file.")
            else:
                go_code = generator.fix_code(go_code, error_log)
                log("Applied fixes to Implementation file.")
            
            save_files(go_code, test_code)
            
            subprocess.run(["go", "mod", "tidy"], cwd=target_dir, capture_output=True, check=False)
        else:
            click.echo(error_log)
            log("Max retries reached or error not fixable.")
            break
    
    if not success:
        click.echo(click.style("\nFAILED: Max retries exceeded or unfixable error.", fg="red", bold=True))

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
    
    click.echo(click.style(f"\nReport generated: {report_file}", fg="blue"))

# Register commands
cli.add_command(index)
cli.add_command(ask)
cli.add_command(migrate_file)

if __name__ == '__main__':
    cli()