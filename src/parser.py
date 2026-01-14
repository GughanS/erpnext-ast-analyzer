import ast
import os

def get_code_chunks(filename):
    """
    Parses a Python file and returns a list of code chunks (functions).
    Each chunk contains: name, line_number, and the actual source code.
    """
    chunks = []
    
    with open(filename, "r", encoding="utf-8") as f:
        source_code = f.read()
        lines = source_code.splitlines()
        tree = ast.parse(source_code)

    class FunctionVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            # 1. Extract the raw source code of the function
            # node.lineno is 1-based, so subtract 1 for list index
            start = node.lineno - 1
            end = node.end_lineno
            function_code = "\n".join(lines[start:end])

            # 2. Create a clean chunk object
            chunks.append({
                "name": node.name,
                "type": "function",
                "content": function_code,
                "filepath": filename,
                "start_line": node.lineno
            })
            self.generic_visit(node)

    FunctionVisitor().visit(tree)
    return chunks