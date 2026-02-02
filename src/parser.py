import ast
import re
import os

def get_code_chunks(filename):
    """
    Tries to parse via AST. If that fails (SyntaxError), 
    falls back to Regex parsing so we don't lose the file.
    """
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        source_code = f.read()

    try:
        # Strategy A: High-Precision AST Parsing
        return parse_via_ast(source_code, filename)
    except SyntaxError as e:
        print(f"⚠️ Syntax Error in {filename}: {e}")
        print("   -> Switching to Fallback Regex Parser...")
        # Strategy B: Low-Precision Regex Parsing (Graceful Degradation)
        return parse_via_regex(source_code, filename)
    except Exception as e:
        print(f" Critical Error processing {filename}: {e}")
        return []

def parse_via_ast(source_code, filename):
    lines = source_code.splitlines()
    tree = ast.parse(source_code)
    chunks = []

    class FunctionVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            start = node.lineno - 1
            end = node.end_lineno
            function_code = "\n".join(lines[start:end])

            chunks.append({
                "name": node.name,
                "type": "function (AST)",
                "content": function_code,
                "filepath": filename,
                "start_line": node.lineno
            })
            self.generic_visit(node)

    FunctionVisitor().visit(tree)
    return chunks

def parse_via_regex(source_code, filename):
    """
    Dumb parser that splits by 'def ' keyword. 
    Used when AST fails due to syntax errors.
    """
    chunks = []
    # Split by lines starting with 'def '
    # This is a heuristic and might capture comments, but it's better than nothing.
    matches = re.finditer(r'(^|\n)def\s+([a-zA-Z_][a-zA-Z0-9_]*)', source_code)
    
    match_list = list(matches)
    lines = source_code.splitlines()
    
    for i, match in enumerate(match_list):
        name = match.group(2)
        start_index = match.start()
        
        # Determine end index (start of next match or end of file)
        if i + 1 < len(match_list):
            end_index = match_list[i+1].start()
            content = source_code[start_index:end_index]
        else:
            content = source_code[start_index:]
            
        # Estimate line number (rough count)
        start_line = source_code[:start_index].count('\n') + 1
        
        chunks.append({
            "name": name,
            "type": "function (Fallback)",
            "content": content.strip(),
            "filepath": filename,
            "start_line": start_line
        })
        
    return chunks