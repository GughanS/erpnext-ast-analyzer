# ERPNext AST Analyzer 🔍

A static analysis tool built to assist in the Legacy Modernization of ERPNext. This tool uses Python's ast (Abstract Syntax Tree) module to extract business logic, dependencies, and side-effects from legacy code modules.

## 🎯 The Problem

Legacy files like sales_invoice.py are massive (2000+ lines) and heavily coupled. Standard LLMs (ChatGPT/Cursor) struggle to identify hidden side-effects like:

Indirect General Ledger (GL) updates.

Stock ledger dependencies.

Asset depreciation triggers.

## 🛠️ The Solution

Instead of treating code as text (Regex), this tool parses the Abstract Syntax Tree to:

Map the API Surface: Identify all 140+ methods in the class.

Trace Side Effects: Find exactly where make_gl_entries is called.

Graph Dependencies: List all external module imports.

## 🚀 How to Run

Clone the repository:

git clone [https://github.com/YOUR_USERNAME/erpnext-ast-analyzer.git](https://github.com/YOUR_USERNAME/erpnext-ast-analyzer.git)
cd erpnext-ast-analyzer


## Run the analyzer:

### Point it to your local ERPNext file
`python analyzer.py`


## 📊 Sample Output

The tool outputs structured JSON ready for AI Agents:
```
{
  "methods_found": 140,
  "business_rules": [
    {
      "source_method": "on_submit",
      "calls": "make_gl_entries",
      "line_number": 473
    }
  ]
}
```

## 🔗 Project Context

Built for the AI Engineering Internship at PearlThoughts.

Focus: Legacy Modernization (Strangler Fig Pattern)

Target: ERPNext Sales Module