import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class CodeGenerator:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def answer(self, query, context_results, mode="explain"):
        """
        mode: 'explain' (default) or 'migrate'
        """
        # Unpack ChromaDB results
        documents = context_results['documents'][0]
        metadatas = context_results['metadatas'][0]
        
        # Build the context string
        context_str = ""
        for i in range(len(documents)):
            meta = metadatas[i]
            context_str += f"\n--- Snippet from {meta['filepath']} (Line {meta['line']}) ---\n"
            context_str += documents[i] + "\n"

        # Select Prompt based on Mode
        if mode == "migrate":
            system_prompt = """You are a Senior Go/Golang Architect.
            Your task is to migrate legacy Python/ERPNext code to modern Go code.
            
            RULES:
            1. Use the provided Python Context to understand the business logic.
            2. Output ONLY valid Go code. 
            3. Use Domain-Driven Design (DDD) patterns (Structs, Methods).
            4. Include comments explaining complex translation logic.
            5. Do NOT wrap in markdown blocks. Just raw code."""
        else:
            # Default Explain Mode
            system_prompt = """You are an Expert Senior Engineer analyzing legacy ERPNext code. 
            Answer the user's question using ONLY the provided code context. 
            
            STRICT OUTPUT FORMATTING RULES:
            1. Output ONLY plain text.
            2. Do NOT use Markdown formatting.
            3. Use standard numbering (1., 2.) for lists."""

        user_message = f"""
        Context Code:
        {context_str}

        Request: {query}
        """

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.1, 
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            return f"Error communicating with Groq: {str(e)}"