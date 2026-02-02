# ERPNext Code Intelligence Tool 

Legacy Modernization Engine for the PearlThoughts AI Internship.
Transforms legacy Python code (ERPNext) into modern Go microservices using AST Analysis and RAG.

## Overview

This tool solves the "Black Box" problem of legacy modernization. Instead of treating code as text (like standard LLMs), it treats code as Structure and Graph.

It uses AST Parsing to extract logic, Vector Databases to index dependencies, and Groq (Llama 3) to generate type-safe Go code that preserves business rules.

## Architecture

![alt text](<Untitled diagram-2026-01-22-043551.png>)    

## Key Features

**AST Indexing:** Parses Python functions to understand structure, not just text.

**RAG Engine:** Uses Google Gemini embeddings to perform semantic search across the codebase.

**Fast Inference:** Powered by Groq (Llama 3.3 70B) for near-instant answers.

**Go Migration:** Automatically generates Domain-Driven Design (DDD) compliant Go code.

**VS Code Integration:** Includes a fully typed TypeScript Extension to ask questions directly in the IDE with real-time streaming.

## Tech Stack

**Language:** Python 3.10+

**Vector DB:** ChromaDB (Local)

**Embeddings:** Google Gemini (text-embedding-004) via REST

**LLM:** Groq (llama-3.3-70b-versatile)

**IDE**: VS Code Extension API

## Setup

### Clone the repository

**1. Python Environment**

```
git clone [https://github.com/YOUR_USERNAME/erpnext-ast-analyzer.git](https://github.com/YOUR_USERNAME/erpnext-ast-analyzer.git)

cd erpnext-ast-analyzer 
```


## Install Dependencies
```
pip install click chromadb groq python-dotenv requests
```

## Configure API Keys
Create a .env file in the root directory:

GOOGLE_API_KEY=AIzaSy...  # From Google AI Studio

GROQ_API_KEY=gsk_...      # From Groq Console


**2. VSCODE EXTENSION**

```
# Navigate to extension folder
cd erpnext-vscode

# Install dependencies & Compile TypeScript
npm install
npm run compile

# Run Debugger
# Press F5 in VS Code

```


## Usage

**Option A: VS Code Extension (Recommended)**

Open the erpnext-vscode folder.

Press F5 to launch the extension.

Use the Command Palette (Ctrl+Shift+P):

ERPNext: Ask AI Logic -> "How does stock update work?"

ERPNext: Migrate to Go -> "Convert on_submit method"

**Option B: CLI Tool**

**Indexing (The Eyes)**

Feed legacy code into the Vector Database.

**Index an entire directory (Recursive)**

`python cli.py index "../erpnext/erpnext/controllers/"`


**Explain Logic (The Teacher)**

Ask the AI to explain complex flows in plain English.

`python cli.py ask "Explain the GL Entry creation logic"`


**Migrate to Go (The Builder)**

Generate a Go code for a specific Python file.

`python cli.py migrate-file "path/to/file.py"`


## Evidence of Effectiveness

We ran a side-by-side comparison between This Tool and Vanilla ChatGPT.

| Feature | Vanilla ChatGPT | ERPNext Intelligence Tool |
|---------|-----------------|---------------------------|
|Context   | Generic Business Rules| Precise Implementation Details
|Dependency Detection| Missed (update_prevdoc_status)| Detected (Temporal Dependency)
|Data Integrity Risk|High (Would corrupt data)|Low (Preserves Logic)

`See full evidence in EVIDENCE.md`

## Project Structure

```

erpnext-ast-analyzer/
├── cli.py              # CLI Entry Point
├── src/                # Core Logic (Parser, Indexer, Search, LLM)
├── data/               # Local Vector Database (Gitignored)
├── generated/          # Output folder for Go code
└── erpnext-vscode/     # VS Code Extension Source
    ├── src/
    │   └── extension.ts # TypeScript Extension Logic
    └── package.json     # Manifest


```


Built by **GUGHAN S** for the **PearlThoughts AI Engineering Internship**.
