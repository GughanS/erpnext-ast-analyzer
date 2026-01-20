# ERPNext AST Analyzer VS Code Extension

This VS Code extension integrates the ERPNext Code Intelligence Tool into your development environment, allowing you to index ERPNext code and query it directly from VS Code.

## Features

- **Index Code**: Index Python files in the ERPNext codebase for analysis.
- **Ask Queries**: Query the indexed code using natural language to get insights and generate Go code.

## Requirements

- Python 3.10+
- The ERPNext AST Analyzer project must be in the parent directory of this extension.
- Required Python packages (install via `pip install -r ../requirements.txt`)

## Installation

1. Clone or copy this extension into your workspace.
2. Run `npm install` to install dependencies.
3. Compile with `npm run compile`.
4. Press F5 to launch the Extension Development Host.

## Usage

1. Open the Command Palette (`Ctrl+Shift+P`).
2. Run `ERPNext AST Analyzer: Index ERPNext Code` to index the codebase.
3. Run `ERPNext AST Analyzer: Ask ERPNext Analyzer` to query the code.

## Development

- Use `npm run watch` to automatically compile on changes.
- Debug with F5 in VS Code.