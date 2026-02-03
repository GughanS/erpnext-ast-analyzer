import os
import re
import time
import logging
import requests
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(dotenv_path=ENV_PATH, override=True)

class CodeGenerator:
    def __init__(self):
        # 1. Load Keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_base = os.getenv("OPENAI_BASE_URL")
        
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        
        # Default Model
        self.model_name = "gpt-4o-mini"
        
        if self.openai_key:
            self.provider = "openai"
            self.api_key = self.openai_key
            logger.info(f"Using OpenAI Provider (Base URL: {self.openai_base if self.openai_base else 'Default'}).")
                
        elif self.google_key:
            self.provider = "google"
            self.api_key = self.google_key
            logger.info("Using Google Gemini as fallback provider.")
        elif self.groq_key:
            self.provider = "groq"
            self.api_key = self.groq_key
            logger.info("Using Groq as fallback provider.")
        else:
            raise ValueError("CRITICAL: No API keys found. Please set OPENAI_API_KEY in .env")

    def _query_openai(self, system_prompt, user_message):
        """Interface for OpenAI Compatible APIs"""
        try:
            from openai import OpenAI
        except ImportError:
            return "// Error: 'openai' library not installed. Run: pip install openai"

        # Initialize client with specific base_url
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.openai_base 
        )
        
        backoff_times = [2, 5, 10]
        
        for i, delay in enumerate(backoff_times):
            try:
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.1, 
                )
                return response.choices[0].message.content
            
            except Exception as e:
                error_msg = str(e).lower()
                # Retry on rate limits or server errors
                if "rate" in error_msg or "limit" in error_msg or "500" in error_msg or "503" in error_msg:
                    logger.warning(f"API Warning (Attempt {i+1}): {error_msg}. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                return f"// OpenAI API Error: {str(e)}"
        
        return "// OpenAI API: Max retries exceeded."

    def _query_groq(self, system_prompt, user_message):
        """Interface for Groq API using Llama 3.3"""
        try:
            from groq import Groq
        except ImportError:
            return "// Error: 'groq' library not installed. Run: pip install groq"

        client = Groq(api_key=self.api_key)
        backoff_times = [2, 5, 10] 
        
        for i, delay in enumerate(backoff_times):
            try:
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.1,
                    max_tokens=8000
                )
                return completion.choices[0].message.content
            except Exception as e:
                time.sleep(delay)
                if i == len(backoff_times) - 1: return f"// Groq Error: {str(e)}"
        return "// Groq Error: Timeout"

    def _query_gemini_with_backoff(self, payload):
        """Fallback to Google Gemini"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        backoff_times = [1, 2, 4, 8]
        
        for i, delay in enumerate(backoff_times):
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    try:
                        text = result['candidates'][0]['content']['parts'][0]['text']
                        if not text.strip(): return "// Error: Empty response"
                        return text
                    except (KeyError, IndexError):
                         return "// Error: Malformed response"
                
                if response.status_code in [429, 500, 503]:
                    time.sleep(delay)
                    continue
                return f"// API Error {response.status_code}: {response.text}"
            except Exception as e:
                if i == len(backoff_times) - 1: return f"// Connection Error: {str(e)}"
                time.sleep(delay)
        return "// Max retries exceeded."

    def _query_llm(self, system_prompt, user_message):
        if self.provider == "openai":
            return self._query_openai(system_prompt, user_message)
        elif self.provider == "groq":
            return self._query_groq(system_prompt, user_message)
        elif self.provider == "google":
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}]
            }
            return self._query_gemini_with_backoff(payload)
        return "// Provider not supported"

    def _clean_code(self, text):
        # 1. Extract explicit code blocks
        text = text.replace('```', '')
        
        match = re.search(r'^\s*package\s+\w+', text, re.MULTILINE)
        if match:
             return text[match.start():].strip()
        
        stripped = text.strip()
        if stripped.startswith("//"):
             return stripped
             
        # Auto-fix missing package
        if "func " in stripped or "import " in stripped:
             return "package main\n\n" + stripped

        return stripped

    def migrate_full_file(self, file_path):
        if not os.path.exists(file_path):
            return "// Error: File not found", "// Error: File not found"

        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        # 1. Implementation
        go_prompt = """You are a Senior Go Architect. Migrate ERPNext logic to Go.
        
        MANDATORY RULES:
        1. Package must be 'main'.
        2. Define ValidationError struct: struct{Message string; Code int; Err error}.
        3. Implement Error() and Unwrap().
        4. Use interfaces for DB calls (e.g., RowScanner) to allow mocking.
        5. DO NOT leave unused imports (like 'fmt') or unused variables.
        6. Start code immediately with 'package main'.
        7. DO NOT write any text/explanations after the code block."""

        go_code = self._clean_code(self._query_llm(go_prompt, source_code))

        if go_code.startswith("//") or "package" not in go_code:
            error_msg = go_code.replace('"', '\\"').replace('\n', ' ')
            go_code = 'package main\n\nimport "fmt"\n\nfunc main() {{ fmt.Println("GENERATION FAILED: {}") }}'.format(error_msg)
            test_code = 'package main\n\nimport "testing"\n\nfunc TestStub(t *testing.T) { t.Fatal("Migration failed: See implementation file") }'
            return go_code, test_code

        # 2. Testing
        # Using .format() to avoid f-string curly brace conflicts
        test_prompt_template = """You are a QA Engineer. Write tests for this Go code.
        
        Code:
        {code}

        CRITICAL MOCKING RULES:
        1. Start output immediately with 'package main'.
        2. **DO NOT REDECLARE** structs, interfaces, or functions from the source code. They are already visible in package 'main'.
        3. Only define **Test functions** (func TestXxx) and **Mock structs**.
        4. When testing ValidationError: use `var vErr *ValidationError` and `errors.As(err, &vErr)`.
        5. Use `mock.MatchedBy` for map arguments in .On() calls.
        6. NEVER try to instantiate `sql.Row` directly. Use an interface.
        """
        
        test_prompt = test_prompt_template.format(code=go_code)

        test_code = self._clean_code(self._query_llm(test_prompt, "Write the tests."))

        return go_code, test_code

    def fix_code(self, original_code, error_log):
        # Safe string formatting for prompt
        prompt_template = """You are a Go Compiler Expert. Fix this Go code based on the compiler errors.
        
        ERROR LOG:
        {error_log}
        
        CODE:
        {original_code}

        TASK:
        1. If "mismatched types *string and untyped string":
           - You are comparing a pointer to a value. Dereference the pointer (e.g., *b.Field == "value") or check for nil first.
           
        2. If "assignment mismatch: ... variables but ... returns ... values":
           - Adjust assignment to match function signature. 
           - If returning (val, error), use: `val, err := func()`
           - If returning (val), use: `val := func()`

        3. If "cannot use ... as ... value in assignment: need type assertion":
           - You are trying to assign an interface{{}} to a concrete type. Use type assertion: val.(string) or val.(int).
           
        4. If "invalid operation: ... (mismatched types int and untyped string)":
           - Check variable definition. Change `var x int` to `var x string` if it holds text.

        5. If "mismatched types string and untyped int" (e.g., comparison > 0):
           - The variable is a string but treated as int. Use `n, _ := strconv.Atoi(val)` then compare `n > 0`.

        6. If "args.Float64 undefined":
           - Testify mocks do not have .Float64(). Use `args.Get(index).(float64)`.
           
        7. If "syntax error: non-declaration statement outside function body":
           - DELETE any text/explanations at the end of the file.
           - Ensure all executable code is inside 'func main()' or 'func init()'.
           
        8. If "expected 'package', found 'EOF'":
           - Ensure file starts with 'package main'.
           
        9. If "mock: Unexpected Method Call":
           - Use `mock.MatchedBy(func(arg map[string]interface{{}}) bool {{ return true }})` for maps.
           
        10. If "unknown field Scan in struct literal of type sql.Row":
           - You CANNOT instantiate `sql.Row` or `sql.Rows` directly.
           - DEFINE an interface `RowScanner` {{ Scan(dest ...interface{{}}) error }}
           - UPDATE code to return `RowScanner`.
           - IMPLEMENT `MockRow`.

        11. If "redeclared in this block":
           - DELETE conflicting definitions from the test file. Keep only `TestXxx` and `MockXxx`.

        12. If "imported and not used":
           - Remove the unused import.

        13. Fix variables/imports. Return ONLY the valid Go code."""
        
        prompt = prompt_template.format(error_log=error_log, original_code=original_code)
        
        return self._clean_code(self._query_llm(prompt, "Fix the code."))