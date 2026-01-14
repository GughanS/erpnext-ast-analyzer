# ERPNext Code Intelligence Tool 

Legacy Modernization Engine for the PearlThoughts AI Internship.
Transforms legacy Python code (ERPNext) into modern Go microservices using AST Analysis and RAG.

## Overview

This tool solves the "Black Box" problem of legacy modernization. Instead of treating code as text (like standard LLMs), it treats code as Structure and Graph.

It uses AST Parsing to extract logic, Vector Databases to index dependencies, and Groq (Llama 3) to generate type-safe Go code that preserves business rules.

## Architecture

    graph LR

    A[Legacy Code] -->|AST Parse| B(Code Chunks)
    B -->|Google Gemini| C(Vector Embeddings)
    C -->|Store| D[(ChromaDB)]
    
    User[Developer] -->|Query| E[CLI Tool]
    E -->|Search| D
    E -->|Context + Prompt| F[Groq LLM]
    F -->|Generate| G[Go Microservice]


## Key Features

**AST Indexing:** Parses Python functions to understand structure, not just text.

**RAG Engine:** Uses Google Gemini embeddings to perform semantic search across the codebase.

**Fast Inference:** Powered by Groq (Llama 3.3 70B) for near-instant answers.

**Go Migration:** Automatically generates Domain-Driven Design (DDD) compliant Go code.

**Parity Validation:** Includes test drivers to verify the new Go code matches Python behavior.

## Tech Stack

**Language:** Python 3.10+

**Vector DB:** ChromaDB (Local)

**Embeddings:** Google Gemini (text-embedding-004) via REST

**LLM:** Groq (llama-3.3-70b-versatile)

**CLI:** Click

## Setup

### Clone the repository

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


## Usage

1. Indexing (The Eyes)

Feed legacy code into the Vector Database.

**Index a single file**

`python cli.py index path/to/sales_invoice.py`

**Index an entire directory (Recursive)**

`python cli.py index ../erpnext/erpnext/controllers/`


2. Semantic Search (The Brain)

Find code based on meaning, not just keywords.

`python cli.py search "How is stock ledger updated?"`


3. Explain Logic (The Teacher)

Ask the AI to explain complex flows in plain English.

`python cli.py ask "Explain the GL Entry creation logic"`


4. Migrate to Go (The Builder)

Generate a Go struct and method for a specific Python function.

`python cli.py migrate "Convert SalesInvoice.on_submit to Go"`


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
├── src/
│   ├── parser.py       # AST Logic extraction
│   ├── indexer.py      # Vector DB & Embeddings
│   ├── search.py       # Semantic Retrieval
│   └── generator.py    # LLM Integration
├── data/               # Local Vector Database (Gitignored)
└── generated/          # Output folder for Go code

```


Built by **GUGHAN S** for the **PearlThoughts AI Engineering Internship**.