import ast
import json
import sys
import os

class ERPNextAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats = {
            "methods_found": 0,
            "business_rules": [],
            "dependencies": set()
        }
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.stats["methods_found"] += 1
        self.current_function = node.name
        
        # Specific logic to analyze the crucial 'on_submit' method
        if node.name == 'on_submit':
            self.analyze_on_submit(node)
        
        # Continue visiting child nodes
        self.generic_visit(node)
        self.current_function = None

    def analyze_on_submit(self, node):
        """
        Drill down into the on_submit method to find what other 
        business logic it triggers.
        """
        for item in node.body:
            # Look for method calls (self.method_name())
            if isinstance(item, ast.Expr) and isinstance(item.value, ast.Call):
                if hasattr(item.value.func, 'attr'):
                    called_method = item.value.func.attr
                    
                    # Store this as a discovered business rule
                    self.stats["business_rules"].append({
                        "source_method": "on_submit",
                        "calls": called_method,
                        "line_number": item.lineno
                    })

    def visit_ImportFrom(self, node):
        """
        Track external dependencies (modules this file needs)
        """
        if node.module:
            self.stats["dependencies"].add(node.module)
        self.generic_visit(node)

def analyze_file(filename):
    # Force UTF-8 reading to handle special characters in source code
    with open(filename, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    analyzer = ERPNextAnalyzer()
    analyzer.visit(tree)
    
    # Convert sets to lists for JSON serialization
    analyzer.stats["dependencies"] = list(analyzer.stats["dependencies"])
    
    return analyzer.stats

if __name__ == "__main__":
    # 1. Try to find the file in the sibling directory (common setup)
    target_file = "../erpnext/accounts/doctype/sales_invoice/sales_invoice.py"
    
    # 2. Fallback: Check if it exists locally or elsewhere
    if not os.path.exists(target_file):
        # Fallback to a relative path assuming you are inside the erpnext repo
        target_file = "erpnext/erpnext/accounts/doctype/sales_invoice/sales_invoice.py"

    try:
        # Print logs to stderr so they don't corrupt the JSON output redirect
        # Also removed emojis to prevent Windows UnicodeEncodeError
        print(f"Analyzing {target_file}...", file=sys.stderr) 
        
        result = analyze_file(target_file)
        
        # Print ONLY JSON to stdout
        print(json.dumps(result, indent=2))
        
        print("Analysis Complete.", file=sys.stderr)
        
    except FileNotFoundError:
        print(f"Error: Could not find file at {target_file}", file=sys.stderr)
        print("Please check the path in analyzer.py line 68", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {str(e)}", file=sys.stderr)