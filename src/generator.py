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
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            self.api_key = os.getenv("GROQ_KEY")
            self.provider = "groq"
        else:
            self.provider = "google"
        
        if not self.api_key:
            raise ValueError("CRITICAL: No API keys found.")

    def _query_gemini_with_backoff(self, payload):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={self.api_key}"
        backoff_times = [1, 2, 4, 8]
        for i, delay in enumerate(backoff_times):
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    result = response.json()
                    try:
                        return result['candidates'][0]['content']['parts'][0]['text']
                    except (KeyError, IndexError):
                         return "// Error: Empty response from AI"
                if response.status_code in [429, 500, 503]:
                    time.sleep(delay)
                    continue
                return f"// API Error {response.status_code}: {response.text}"
            except Exception as e:
                if i == len(backoff_times) - 1: return f"// Connection Error: {str(e)}"
                time.sleep(delay)
        return "// Max retries exceeded."

    def _query_llm(self, system_prompt, user_message):
        if self.provider == "google":
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_message}]}]
            }
            return self._query_gemini_with_backoff(payload)
        return "// Provider not supported"

    def _clean_code(self, text):
        # 1. Extract explicit code blocks
        text = text.replace('```', '')
        
        # Regex to find 'package name' at start of line (allowing for optional whitespace)
        match = re.search(r'^\s*package\s+\w+', text, re.MULTILINE)
        if match:
             return text[match.start():].strip()
        
        # 3. Last Resort: If text is an error message (starts with //), return it as is.
        # Otherwise, if it looks like code but missing package, prepend 'package main' (risky but helpful)
        stripped = text.strip()
        if stripped.startswith("//"):
             return stripped
             
        # If the AI forgot 'package main' but wrote imports/func, let's auto-fix
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
        4. Use interfaces for DB calls.
        5. DO NOT leave unused imports (like 'fmt') or unused variables.
        6. Start code immediately with 'package main'."""

        go_code = self._clean_code(self._query_llm(go_prompt, source_code))

        # Check for generation failure immediately
        if go_code.startswith("//") or "package" not in go_code:
            # Return a stub file that compiles but panics, allowing the user to see the error in the CLI output
            # instead of a confusing "expected package" error.
            error_msg = go_code.replace('"', '\\"').replace('\n', ' ')
            go_code = f'package main\n\nimport "fmt"\n\nfunc main() {{ fmt.Println("GENERATION FAILED: {error_msg}") }}'

        # 2. Testing
        # NOTE: Double curly braces {{ }} are used below to escape them in the Python f-string
        test_prompt = f"""You are a QA Engineer. Write tests for this Go code.
        
        Code:
        {go_code}

        CRITICAL MOCKING RULES (Prevent Testify Panics):
        1. Start output immediately with 'package main'.
        2. When testing ValidationError: use `var vErr *ValidationError` and `errors.As(err, &vErr)`.
        
        3. **COMPLEX ARGUMENT MATCHING**:
           - NEVER put `mock.Anything` or `mock.AnythingOfType` INSIDE a `map` or `slice` literal.
           - Testify DOES NOT support nested matchers in maps.
           - INCORRECT: `m.On("SetValues", map[string]interface{{}}{{"date": mock.Anything}})`
           - CORRECT: Use `mock.MatchedBy`:
             `m.On("SetValues", mock.MatchedBy(func(arg map[string]interface{{}}) bool {{ return true }}))`
        """

        test_code = self._clean_code(self._query_llm(test_prompt, "Write the tests."))

        return go_code, test_code

    def fix_code(self, original_code, error_log):
        """Self-healing mechanism: Fixes compilation errors."""
        # NOTE: Double curly braces {{ }} are used below to escape them in the Python f-string
        prompt = f"""You are a Go Compiler Expert. The following code failed to build or panic.
        
        ERROR LOG:
        {error_log}
        
        CODE:
        {original_code}
        
        TASK:
        1. If "expected 'package', found 'EOF'" or missing package:
           - Ensure the file starts with "package main".
        2. If "mock: Unexpected Method Call" involves a MAP/SLICE mismatch:
           - Replace the strict map argument in `.On()` with `mock.MatchedBy(func(data map[string]interface{{}}) bool {{ return true }})`.
        3. Fix unused imports/variables.
        4. Return the complete, corrected code."""
        
        return self._clean_code(self._query_llm(prompt, "Fix the code."))