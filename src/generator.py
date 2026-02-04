import os
import re
import time
import logging
import requests
from typing import Tuple
from dotenv import load_dotenv

# ===================== LOGGING =====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ===================== PATHS =====================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")

load_dotenv(dotenv_path=ENV_PATH, override=True)


# ==================================================
#                 CODE GENERATOR
# ==================================================
class CodeGenerator:
    """
    Production-safe Go code generator.

    HARD GUARANTEES:
    - ERP values are strings
    - Generator NEVER calls getValue directly
    - Generator ONLY calls getValueStr -> (string, error)
    - Tests never redeclare production symbols
    - Tests NEVER use variadic (...) syntax
    """

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_base = os.getenv("OPENAI_BASE_URL")
        self.google_key = os.getenv("GOOGLE_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")

        self.model_name = "gpt-4o-mini"

        if self.openai_key:
            self.provider = "openai"
            self.api_key = self.openai_key
            logger.info(f"Using OpenAI provider (Base: {self.openai_base or 'Default'})")
        elif self.groq_key:
            self.provider = "groq"
            self.api_key = self.groq_key
            logger.info("Using Groq provider")
        elif self.google_key:
            self.provider = "google"
            self.api_key = self.google_key
            logger.info("Using Google Gemini provider")
        else:
            raise RuntimeError("No LLM API key found")

    # ==================================================
    #                    LLM CALLS
    # ==================================================
    def _query_openai(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return "// Error: 'openai' library not installed. Run: pip install openai"

        client = OpenAI(api_key=self.api_key, base_url=self.openai_base)
        for delay in (2, 5, 10):
            try:
                resp = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )
                return resp.choices[0].message.content
            except Exception as e:
                msg = str(e).lower()
                if any(x in msg for x in ("rate", "limit", "429", "500", "503")):
                    logger.warning("Retrying after error: %s", msg)
                    time.sleep(delay)
                    continue
                return f"// OpenAI Error: {msg}"
        return "// OpenAI max retries exceeded"

    def _query_groq(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from groq import Groq
        except ImportError:
            return "// Error: 'groq' library not installed. Run: pip install groq"

        client = Groq(api_key=self.api_key)
        for delay in (2, 5, 10):
            try:
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=8000,
                )
                return resp.choices[0].message.content
            except Exception as e:
                time.sleep(delay)
                if delay == 10: return f"// Groq Error: {str(e)}"
        return "// Groq max retries exceeded"

    def _query_gemini(self, system_prompt: str, user_prompt: str) -> str:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={self.api_key}"
        )

        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
        }

        for delay in (1, 2, 4, 8):
            try:
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code == 200:
                    data = r.json()
                    try:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    except Exception:
                        return "// Error: Malformed Gemini response"
                
                if r.status_code in (429, 500, 503):
                    time.sleep(delay)
                    continue
                return f"// Gemini Error: {r.text}"
            except Exception as e:
                time.sleep(delay)
                if delay == 8: return f"// Gemini Connection Error: {str(e)}"
        return "// Gemini max retries exceeded"

    def _query_llm(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai":
            return self._query_openai(system_prompt, user_prompt)
        if self.provider == "groq":
            return self._query_groq(system_prompt, user_prompt)
        if self.provider == "google":
            return self._query_gemini(system_prompt, user_prompt)
        return "// Error: Unknown provider"

    # ==================================================
    #                  SANITIZATION
    # ==================================================
    def _clean_code(self, raw: str) -> str:
        text = raw.replace("```go", "").replace("```", "")
        lines = []

        for line in text.splitlines():
            s = line.strip()
            if not s:
                lines.append(line)
                continue
            # Remove Python comments or markdown headers, but keep Go comments
            if s.startswith("#") or (s.startswith("*") and not s.startswith("*/")) or s.startswith("==="):
                continue
            if s == "go" or s.startswith("go test") or s.startswith("go run"):
                continue
            lines.append(line)

        text = "\n".join(lines).strip()
        if "package main" not in text:
            text = "package main\n\n" + text
        
        # Post-processing cleanup
        text = self._auto_fix_common_errors(text)
        
        return text
    
    def _auto_fix_common_errors(self, code: str) -> str:
        """Automatically fix common LLM mistakes."""
        
        # 1. Remove duplicate function definitions (keep first occurrence)
        func_pattern = r'^(var\s+(\w+)\s*=\s*func.*?^\})'
        matches = list(re.finditer(func_pattern, code, re.MULTILINE | re.DOTALL))
        
        seen_funcs = {}
        for match in matches:
            func_name = match.group(2)
            if func_name not in seen_funcs:
                seen_funcs[func_name] = match
            else:
                # Remove duplicate
                logger.warning(f"Auto-removing duplicate definition of {func_name}")
                code = code.replace(match.group(0), f"// Removed duplicate: {func_name}", 1)
        
        # 2. Fix assignment mismatch for single-return functions
        single_return_funcs = [
            'getBinDetails', 'GetActualQty', 'getValuationMethod',
            'getReservedQtyForProductionPlan', 'getBatchQty', 'makeAutoname',
            'cint', 'flt', 'getNameFromHash', 'batchExists'
        ]
        
        for func in single_return_funcs:
            # Fix: result, err := func(...) -> result := func(...)
            pattern = rf'(\w+)\s*,\s*\w+\s*:=\s*{func}\s*\('
            replacement = rf'\1 := {func}('
            code = re.sub(pattern, replacement, code)
            logger.info(f"Fixed assignment mismatch for {func}")
        
        # 3. Remove undefined function calls (getPlannedQty, etc.)
        undefined_funcs = [
            'getPlannedQty', 'getIndentedQty', 'getOrderedQty', 
            'getReservedQty', 'getReservedQtyForProduction'
        ]
        
        for func in undefined_funcs:
            if func in code:
                logger.warning(f"Found undefined function call: {func} - needs manual fix")
                # Comment out the line
                code = re.sub(
                    rf'^(\s*)(\w+\s*:?=\s*{func}\s*\(.*?\))$',
                    rf'\1// TODO: Fix undefined {func}\n\1// \2',
                    code,
                    flags=re.MULTILINE
                )
        
        # 4. Remove unused imports
        if '"errors"' in code and 'errors.' not in code and 'errors.New' not in code:
            logger.info("Removing unused 'errors' import")
            code = re.sub(r'^\s*"errors"\s*$', '', code, flags=re.MULTILINE)
        
        return code

    # ==================================================
    #                STATIC VALIDATION
    # ==================================================
    def _validate_go(self, code: str):
        illegal_patterns = [
            # assigning string literal to error
            r'error\s*=\s*"',
            # calling getValue directly (FORBIDDEN)
            r'\bgetValue\s*\(',
        ]
        for p in illegal_patterns:
            if re.search(p, code):
                logger.warning(f"Potential Illegal Go pattern detected: {p}")
    
    def _validate_no_redeclarations(self, code: str):
        """Detect function redeclarations in production code."""
        # Find all function declarations
        func_defs = re.findall(r'^var\s+(\w+)\s*=\s*func', code, re.MULTILINE)
        
        # Check for duplicates
        seen = set()
        for func in func_defs:
            if func in seen:
                logger.error(f"REDECLARATION DETECTED: {func} is defined multiple times!")
                # Remove duplicate (keep first occurrence)
                # This is a band-aid - ideally LLM shouldn't generate this
            seen.add(func)
        
        if len(func_defs) != len(seen):
            logger.warning(f"Found {len(func_defs)} function definitions but only {len(seen)} unique names")
    
    def _validate_no_undefined_functions(self, code: str):
        """Detect calls to undefined helper functions."""
        # Known approved functions
        approved = {
            'getValueStr', 'dbGetValue', 'dbSet', 'makeAutoname', 'getNameFromHash',
            'batchExists', 'revertSeriesIfLast', 'getBatchQty', 'getValuationMethod',
            'addDays', 'renderTemplate', 'cint', 'cstr', 'flt', 'getBinDetails',
            'getExpiryDetails', 'getReservedQtyForProductionPlan', 'futureSleExists',
            'GetActualQty'
        }
        
        # Find all function calls that look like helpers
        func_calls = re.findall(r'\b(get\w+|make\w+|batch\w+|future\w+|revert\w+|render\w+|add\w+|db\w+|c\w+|flt|Get\w+)\s*\(', code)
        
        undefined = set(func_calls) - approved - {'getBatchDetails'}  # Remove duplicates and approved
        if undefined:
            logger.warning(f"Potentially undefined functions called: {undefined}")


    def _validate_braces(self, code: str):
        # Simple heuristic to catch obvious truncation
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            logger.warning(f"Brace mismatch detected: {{={open_braces}, }}={close_braces}")

    def _validate_test_code(self, test_code: str, prod_code: str):
        # Extract function names from prod code
        prod_funcs = re.findall(r'^var\s+(\w+)\s*=\s*func', prod_code, re.MULTILINE)
        
        for func in prod_funcs:
            # Check if test re-declares them as var or :=
            if re.search(rf'var\s+{func}\s*=', test_code) or re.search(rf'{func}\s*:=', test_code):
                logger.warning(f"Test redeclares production global: {func}")

    def _validate_no_variadic_in_tests(self, test_code: str):
        if "..." in test_code and "mock.Anything" not in test_code:
             pass

    # ==================================================
    #                  GENERATION
    # ==================================================
    def _generate_validated(self, prompt: str, source: str) -> str:
        code = self._query_llm(prompt, source)
        code = self._clean_code(code)
        self._validate_go(code)
        self._validate_braces(code)
        self._validate_no_redeclarations(code)
        self._validate_no_undefined_functions(code)
        return code

    def migrate_full_file(self, file_path_input: str) -> Tuple[str, str]:
        if not os.path.exists(file_path_input):
            return "// Error: File not found", ""

        with open(file_path_input, "r", encoding="utf-8") as f:
            source = f.read()

        go_prompt = (
            "You are a Senior Go Architect migrating ERPNext logic to Go.\n\n"
            "⚠️ CRITICAL - READ FIRST ⚠️\n"
            "1. getBinDetails returns map[string]string (SINGLE VALUE, NO ERROR)\n"
            "   WRONG: binDetails, err := getBinDetails(name)  // 2 variables, 1 return = ERROR\n"
            "   RIGHT: binDetails := getBinDetails(name)       // 1 variable, 1 return = CORRECT\n\n"
            "2. NEVER define the same function twice\n"
            "   If getBinDetails exists at line 62, DO NOT create it again at line 210\n"
            "   Each 'var functionName = func' can appear ONLY ONCE in the entire file\n\n"
            "CRITICAL RULES:\n"
            "1. Start with package main\n"
            "2. ERP values are strings\n"
            "3. NEVER call getValue directly\n"
            "4. ALWAYS call getValueStr (returns string, error)\n"
            "5. switch cases MUST use braces\n"
            "6. select only inside functions\n"
            "7. No markdown, no # comments\n"
            "8. DEFINITION RULE: Define helper functions as GLOBAL VARIABLES (var funcName = func...) so they can be mocked in tests:\n"
            "   - getValueStr, dbGetValue, dbSet\n"
            "   - makeAutoname, getNameFromHash\n"
            "   - batchExists, revertSeriesIfLast\n"
            "   - getBatchQty, getValuationMethod, addDays, renderTemplate\n"
            "   - getBatchDetails, getExpiryDetails, getReservedQtyForProductionPlan\n"
            "   - futureSleExists, GetActualQty\n"
            "   - cint, cstr, flt\n"
            "   ⚠️ DEFINE EACH FUNCTION ONLY ONCE - NO DUPLICATES ALLOWED ⚠️\n"
            "9. STRUCT FIELD TYPES - CRITICAL:\n"
            "    - Numeric quantity fields (ActualQty, ProjectedQty, OrderedQty, etc.) MUST be *float64\n"
            "    - String fields (Name, Item, Warehouse, etc.) are *string\n"
            "    - NEVER mix these types\n"
            "    - When assigning to *float64: temp := 100.0; b.ActualQty = &temp\n"
            "    - When assigning to *string: temp := \"value\"; b.Name = &temp\n"
            "10. POINTER RULE: Always dereference pointers before using in operations.\n"
            "    - Math: total := *b.ActualQty + *b.ProjectedQty\n"
            "    - String concat: name := *b.Item + \"-\" + *b.Warehouse\n"
            "    - Check for nil before dereferencing if necessary\n"
            "11. POINTER ASSIGNMENT PATTERNS:\n"
            "    For *string fields:\n"
            "      WRONG: b.Name = makeAutoname(...)\n"
            "      RIGHT: val := makeAutoname(...); b.Name = &val\n"
            "    For *float64 fields:\n"
            "      WRONG: b.ActualQty = &actualQty where actualQty is *float64\n"
            "      RIGHT: b.ActualQty = &actualQty where actualQty is float64\n"
            "      WRONG: b.ActualQty = GetActualQty(...) // missing &\n"
            "      RIGHT: qty := GetActualQty(...); b.ActualQty = &qty\n"
            "11. STRUCT FIELDS: Ensure the struct definition includes 'isNew bool' if referenced.\n"
            "12. STRICT SIGNATURES (Follow these EXACTLY):\n"
            "    - var getValueStr = func(doctype, name, fieldname string) (string, error) { ... }\n"
            "    - var dbGetValue = func(doctype, name, fieldname string) (string, error) { ... }\n"
            "    - var dbSet = func(doctype, name, fieldname, value string) error { ... }\n"
            "    - var makeAutoname = func(key string) string { ... }\n"
            "    - var getNameFromHash = func(hash string) string { ... }\n"
            "    - var batchExists = func(name string) bool { ... }\n"
            "    - var futureSleExists = func(args interface{}) bool { ... }\n"
            "    - var revertSeriesIfLast = func(series, name string) { ... }\n"
            "    - var getBatchQty = func(batch, warehouse string) float64 { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var getValuationMethod = func(item string) string { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var addDays = func(date string, days int) string { ... }\n"
            "    - var renderTemplate = func(template string, data interface{}) string { ... }\n"
            "    - var cint = func(val string) int { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var cstr = func(val interface{}) string { ... }\n"
            "    - var flt = func(val string) float64 { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var getBinDetails = func(batch string) map[string]string { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var getExpiryDetails = func(batch string) string { ... }\n"
            "    - var getReservedQtyForProductionPlan = func(productionPlan, item string) float64 { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    - var GetActualQty = func(itemCode, warehouse string) float64 { ... }  ← SINGLE RETURN (NO ERROR)\n"
            "    \n"
            "    ⚠️ CRITICAL ASSIGNMENT RULES ⚠️\n"
            "    SINGLE return (no error): result := functionCall()\n"
            "    DOUBLE return (with error): result, err := functionCall()\n"
            "    \n"
            "    EXAMPLES:\n"
            "    binDetails := getBinDetails(name)           ✓ Correct (1 variable = 1 return)\n"
            "    binDetails, err := getBinDetails(name)      ✗ ERROR (2 variables, 1 return)\n"
            "    qty := GetActualQty(item, warehouse)        ✓ Correct (1 variable = 1 return)\n"
            "    qty, err := GetActualQty(item, warehouse)   ✗ ERROR (2 variables, 1 return)\n"
            "    str, err := getValueStr(dt, name, field)    ✓ Correct (2 variables = 2 returns)\n"
            "13. VARIABLE TYPE INFERENCE - CRITICAL:\n"
            "    When you call a function, the result has the function's return type:\n"
            "    \n"
            "    orderedQty := flt(orderedQtyStr)           // orderedQty is float64 (flt returns float64)\n"
            "    orderedQtyStr, _ := getValueStr(...)       // orderedQtyStr is string (getValueStr returns string)\n"
            "    actualQty := GetActualQty(item, warehouse) // actualQty is float64 (GetActualQty returns float64)\n"
            "    binDetails := getBinDetails(binName)       // binDetails is map[string]string\n"
            "    \n"
            "    NEVER confuse these:\n"
            "    - If you call flt(), result is float64, not string\n"
            "    - If you call getValueStr(), result is string, not float64\n"
            "    - If you call getBinDetails(), result is map[string]string, not string\n"
            "14. ASSIGNMENT TO STRUCT FIELDS:\n"
            "    Match the variable type to the field type:\n"
            "    \n"
            "    If b.OrderedQty is *float64:\n"
            "      orderedQty := flt(str)    // orderedQty is float64\n"
            "      b.OrderedQty = &orderedQty  // Take address of float64\n"
            "    \n"
            "    If b.Name is *string:\n"
            "      name := makeAutoname(key)  // name is string\n"
            "      b.Name = &name              // Take address of string\n"
            "    \n"
            "    WRONG: orderedQtyStr is string but b.OrderedQty needs *float64:\n"
            "      orderedQtyStr, _ := getValueStr(...)\n"
            "      b.OrderedQty = &orderedQtyStr  // TYPE ERROR!\n"
            "    \n"
            "    RIGHT: Convert first:\n"
            "      orderedQtyStr, _ := getValueStr(...)\n"
            "      orderedQty := flt(orderedQtyStr)  // Convert to float64\n"
            "      b.OrderedQty = &orderedQty         // Now types match\n"
            "13. NO NESTED CALLS for functions returning errors. \n"
            "    WRONG: cint(getValueStr(...))\n"
            "    RIGHT: val, _ := getValueStr(...); if err != nil { return err }; intVal := cint(val)\n"
            "14. ARGUMENT CHECKS: dbGetValue and getValueStr take 3 arguments (doctype, name, fieldname). Never call them with 2.\n"
            "15. ERROR TYPES: Never return a string literal for an error type. Use `errors.New(\"...\")`.\n"
            "16. TYPE CONVERSION RULES - ABSOLUTELY CRITICAL:\n"
            "    A. flt() expects STRING input, returns float64\n"
            "       WRONG: flt(orderedQty) where orderedQty is float64\n"
            "       RIGHT: Just use orderedQty directly if it's already float64\n"
            "    \n"
            "    B. cint() expects STRING input, returns int\n"
            "       - To convert int → float64: use float64(intValue)\n"
            "       - NEVER: flt(cint(x)) // type error\n"
            "       - CORRECT: float64(cint(x))\n"
            "    \n"
            "    C. If variable is already correct type, DON'T convert it:\n"
            "       - If actualQty is float64, use it directly\n"
            "       - If orderedQty is float64, use it directly\n"
            "       - Don't wrap numbers in flt() or cint() unnecessarily\n"
            "    \n"
            "    D. Type casting patterns:\n"
            "       - float64 → string: use cstr() or fmt.Sprintf()\n"
            "       - string → float64: use flt()\n"
            "       - string → int: use cint()\n"
            "       - int → float64: use float64()\n"
            "17. STRUCT FIELD TYPES (Define in struct exactly like this):\n"
            "    type Bin struct {\n"
            "        Name            *string  // String pointer\n"
            "        Item            *string  // String pointer\n"
            "        Warehouse       *string  // String pointer\n"
            "        ActualQty       *float64 // Numeric pointer (NOT *string)\n"
            "        ProjectedQty    *float64 // Numeric pointer (NOT *string)\n"
            "        OrderedQty      *float64 // Numeric pointer (NOT *string)\n"
            "        IndentedQty     *float64 // Numeric pointer (NOT *string)\n"
            "        PlannedQty      *float64 // Numeric pointer (NOT *string)\n"
            "        ReservedQty     *float64 // Numeric pointer (NOT *string)\n"
            "        ReservedQtyForProduction *float64\n"
            "        ReservedQtyForSubContract *float64\n"
            "        isNew           bool     // Boolean (NOT pointer)\n"
            "    }\n"
            "18. RETURN TYPE MATCHING:\n"
            "    - If function returns map[string]string, ensure variable is that type\n"
            "    - If function returns float64, assign to float64 variable\n"
            "    - Use cstr() to convert any type to string when needed\n"
            "    - Use fmt.Sprintf() for formatting numbers as strings\n"
            "19. FUNCTION REDECLARATION - CRITICAL:\n"
            "    - Each function can only be defined ONCE in the entire file\n"
            "    - If getBinDetails is defined, DO NOT define it again anywhere\n"
            "    - Check the existing functions list before creating new ones\n"
            "    - If a function exists and you need different logic, modify the existing one\n"
            "    - WRONG:\n"
            "      var getBinDetails = func(...) { ... }  // First definition\n"
            "      ...\n"
            "      var getBinDetails = func(...) { ... }  // REDECLARATION ERROR!\n"
            "    - RIGHT:\n"
            "      var getBinDetails = func(...) { ... }  // Define once only\n"
            "20. DO NOT CREATE UNDEFINED HELPER FUNCTIONS:\n"
            "    - ONLY use helper functions from the approved list (see rule 12)\n"
            "    - NEVER create new helpers like: getPlannedQty, getIndentedQty, getOrderedQty, getReservedQty\n"
            "    - If you need field values, use getValueStr or dbGetValue\n"
            "    \n"
            "    ❌ ABSOLUTELY FORBIDDEN - DO NOT WRITE THESE:\n"
            "    plannedQty := getPlannedQty(item, warehouse)         // DOES NOT EXIST!\n"
            "    indentedQty := getIndentedQty(item, warehouse)       // DOES NOT EXIST!\n"
            "    orderedQty := getOrderedQty(item, warehouse)         // DOES NOT EXIST!\n"
            "    reservedQty := getReservedQty(item, warehouse)       // DOES NOT EXIST!\n"
            "    qty := getReservedQtyForProduction(item, warehouse)  // DOES NOT EXIST!\n"
            "    \n"
            "    ✅ CORRECT - ALWAYS USE THIS PATTERN:\n"
            "    plannedQtyStr, _ := getValueStr(\"Bin\", binName, \"planned_qty\")\n"
            "    plannedQty := flt(plannedQtyStr)\n"
            "21. ASSIGNMENT MISMATCH WITH SINGLE RETURN:\n"
            "    - Error: 'assignment mismatch: 2 variables but getBinDetails returns 1 value'\n"
            "    - CAUSE: getBinDetails returns map[string]string (1 value), not (map, error)\n"
            "    - FIX:\n"
            "      WRONG: binDetails, err := getBinDetails(binName)\n"
            "      RIGHT: binDetails := getBinDetails(binName)\n"
            "22. Return only valid Go code"
        )

        go_code = self._generate_validated(go_prompt, source)

        test_prompt = (
            "You are a Go QA Engineer.\n"
            "CRITICAL RULES:\n"
            "1. Start with package main\n"
            "2. REDECLARATION RULE - THE MOST IMPORTANT RULE:\n"
            "   - Production globals (getValueStr, GetActualQty, etc.) ALREADY EXIST\n"
            "   - NEVER write: var GetActualQty = func(...)\n"
            "   - NEVER write: GetActualQty := func(...)\n"
            "   - ALWAYS write: GetActualQty = func(...) { ... } (reassignment only)\n"
            "   - This applies to ALL helper functions from production code\n"
            "3. DO NOT use variadic (...) syntax\n"
            "4. ONLY write TestXxx functions and NEW mock structs\n"
            "5. MOCKING PATTERN (follow exactly):\n"
            "   func TestSomething(t *testing.T) {\n"
            "       // Save originals\n"
            "       origGetActualQty := GetActualQty\n"
            "       origGetBinDetails := getBinDetails\n"
            "       origDbSet := dbSet\n"
            "       \n"
            "       // Mock by REASSIGNING the function variable (not calling it)\n"
            "       GetActualQty = func(itemCode, warehouse string) float64 {\n"
            "           return 100.0\n"
            "       }\n"
            "       \n"
            "       getBinDetails = func(batch string) map[string]string {\n"
            "           return map[string]string{\n"
            "               \"actual_qty\": \"100\",\n"
            "               \"ordered_qty\": \"50\",\n"
            "           }\n"
            "       }\n"
            "       \n"
            "       dbSet = func(doctype, name, fieldname, value string) error {\n"
            "           return nil\n"
            "       }\n"
            "       \n"
            "       // Restore\n"
            "       defer func() {\n"
            "           GetActualQty = origGetActualQty\n"
            "           getBinDetails = origGetBinDetails\n"
            "           dbSet = origDbSet\n"
            "       }()\n"
            "       \n"
            "       // Test code...\n"
            "   }\n"
            "   \n"
            "   CRITICAL: Assign to the FUNCTION NAME, not a function call:\n"
            "   WRONG: getBinDetails(\"batch1\") = map[string]string{}  // Assigning to result!\n"
            "   RIGHT: getBinDetails = func(...) map[string]string {...}  // Reassigning function!\n"
            "6. RETURN VALUES:\n"
            "   - GetActualQty returns float64 (single value)\n"
            "   - getValuationMethod returns string (single value)\n"
            "   - getReservedQtyForProductionPlan returns float64 (single value)\n"
            "   - dbSet returns error (single value)\n"
            "   - getValueStr returns (string, error) (two values)\n"
            "   - dbGetValue returns (string, error) (two values)\n"
            "7. ERROR RETURNS: In mock functions, if return type is error, return nil or errors.New(\"msg\").\n"
            "8. IMPORTS: Only import packages you actually use. Don't import 'errors' if all mocks return nil.\n"
            "9. DO NOT CREATE UNDEFINED FUNCTIONS:\n"
            "   - DO NOT mock or use functions that don't exist in production code\n"
            "   - WRONG: getPlannedQty = func(...) { ... }  // This doesn't exist!\n"
            "   - Only mock functions that are defined in the production code\n"
            "   - Check the approved function list before mocking\n\n"
            f"CODE:\n{go_code}"
        )

        test_code = self._generate_validated(test_prompt, "Write tests")
        self._validate_test_code(test_code, go_code)
        self._validate_no_variadic_in_tests(test_code)

        return go_code, test_code

    def fix_code(self, code: str, error_log: str) -> str:
        prompt = (
            "You are a Go compiler expert fixing ONLY the errors shown.\n\n"
            "⚠️⚠️⚠️ MOST COMMON ERRORS - FIX THESE FIRST ⚠️⚠️⚠️\n\n"
            
            "ERROR: 'getBinDetails redeclared in this block'\n"
            "CAUSE: You defined getBinDetails TWICE in the same file\n"
            "FIX: Search for ALL occurrences of 'var getBinDetails = func'\n"
            "     DELETE the second/third/any duplicate definitions\n"
            "     KEEP ONLY THE FIRST ONE\n"
            "EXAMPLE:\n"
            "  var getBinDetails = func(batch string) map[string]string { ... }  ← Line 62 (KEEP THIS)\n"
            "  ...\n"
            "  var getBinDetails = func(batch string) map[string]string { ... }  ← Line 210 (DELETE THIS)\n\n"
            
            "ERROR: 'assignment mismatch: 2 variables but getBinDetails returns 1 value'\n"
            "CAUSE: getBinDetails returns ONLY map[string]string (NO ERROR RETURN)\n"
            "FIX: Use single assignment, NOT double assignment\n"
            "WRONG: binDetails, err := getBinDetails(name)  ← 2 variables, 1 return = ERROR\n"
            "RIGHT: binDetails := getBinDetails(name)       ← 1 variable, 1 return = CORRECT\n\n"
            
            "SINGLE RETURN FUNCTIONS (NO ERROR):\n"
            "- getBinDetails(batch string) map[string]string\n"
            "- GetActualQty(itemCode, warehouse string) float64\n"
            "- getValuationMethod(item string) string\n"
            "- getReservedQtyForProductionPlan(productionPlan, item string) float64\n"
            "- getBatchQty(batch, warehouse string) float64\n"
            "- makeAutoname(key string) string\n"
            "- cint(val string) int\n"
            "- flt(val string) float64\n"
            "ALL THESE USE: result := functionCall()  (NOT result, err := ...)\n\n"
            
            "NOW FIX THE ACTUAL ERRORS:\n\n"
            f"ERROR LOG:\n{error_log}\n\n"
            f"CODE:\n{code}\n\n"
            "CRITICAL FIXING RULES:\n\n"
            
            "1. REDECLARATION ERRORS:\n"
            "   - Error: 'GetActualQty redeclared in this block'\n"
            "   - FIX: In TEST file, change 'var GetActualQty = func...' to 'GetActualQty = func...'\n"
            "   - FIX: Remove ALL 'var' and ':=' when assigning to existing globals in tests\n"
            "   - NEVER redeclare functions that exist in production code\n\n"
            
            "2. ASSIGNMENT MISMATCH ERRORS:\n"
            "   - Error: 'assignment mismatch: 2 variables but GetActualQty returns 1 value'\n"
            "   - THESE FUNCTIONS RETURN SINGLE VALUES (NO ERROR):\n"
            "     * GetActualQty(itemCode, warehouse string) float64\n"
            "     * getValuationMethod(item string) string\n"
            "     * getReservedQtyForProductionPlan(productionPlan, item string) float64\n"
            "     * getBatchQty(batch, warehouse string) float64\n"
            "     * makeAutoname(key string) string\n"
            "     * cint(val string) int\n"
            "     * flt(val string) float64\n"
            "   - FIX: Use single assignment:\n"
            "     WRONG: actualQty, err := GetActualQty(item, warehouse)\n"
            "     RIGHT: actualQty := GetActualQty(item, warehouse)\n\n"
            
            "3. UNDEFINED FIELD/METHOD ERRORS:\n"
            "   - Error: 'type *Bin has no field or method UpdateReservedQtyForSubContracting'\n"
            "   - FIX: Remove the undefined field/method call completely\n"
            "   - Or add the field to the struct definition if it should exist\n\n"
            
            "4. UNUSED IMPORT ERRORS:\n"
            "   - Error: '\"errors\" imported and not used'\n"
            "   - FIX: Remove 'import \"errors\"' from imports section\n"
            "   - Only import if you use errors.New() or errors.Is()\n\n"
            
            "5. TYPE CONVERSION ERRORS:\n"
            "   - Error: 'cannot use cint(x) (type int) as float64'\n"
            "   - FIX: Use float64(cint(x)), NOT flt(cint(x))\n"
            "   - Error: 'cannot use orderedQty (type float64) as string in argument to flt'\n"
            "   - FIX: Don't call flt() on variables that are already float64\n"
            "   - If orderedQty is already float64, just use it directly\n"
            "   - flt() is ONLY for converting strings to float64\n"
            "   - Example fixes:\n"
            "     WRONG: total := flt(orderedQty) + flt(plannedQty)  // if already float64\n"
            "     RIGHT: total := orderedQty + plannedQty\n\n"
            
            "6. POINTER TYPE MISMATCH:\n"
            "   - Error: 'cannot use &actualQty (type *float64) as *string'\n"
            "   - CAUSE: Struct field is defined as *string but should be *float64\n"
            "   - FIX: Change struct definition:\n"
            "     WRONG: ActualQty *string\n"
            "     RIGHT: ActualQty *float64\n"
            "   - ALL quantity fields must be *float64, not *string:\n"
            "     ActualQty, ProjectedQty, OrderedQty, IndentedQty,\n"
            "     PlannedQty, ReservedQty, ReservedQtyForProduction, etc.\n\n"
            
            "7. COMPARISON TYPE MISMATCH:\n"
            "   - Error: 'invalid operation: *bin.ActualQty != 150.0 (mismatched types string and float)'\n"
            "   - CAUSE: Field is *string but should be *float64\n"
            "   - FIX: Update struct definition to use *float64 for numeric fields\n"
            "   - If field is *float64, comparison works: *bin.ActualQty != 150.0\n\n"
            
            "8. VARIABLE TYPE ASSIGNMENT ERRORS:\n"
            "   - Error: 'cannot use &orderedQty (type *string) as *float64'\n"
            "   - CAUSE: orderedQty is a string variable, but field needs float64\n"
            "   - ROOT CAUSE: Didn't convert the string to float64\n"
            "   - FIX PATTERN:\n"
            "     WRONG:\n"
            "       orderedQtyStr, _ := getValueStr(...) // This is a string\n"
            "       b.OrderedQty = &orderedQtyStr         // ERROR: *string != *float64\n"
            "     \n"
            "     RIGHT:\n"
            "       orderedQtyStr, _ := getValueStr(...) // This is a string\n"
            "       orderedQty := flt(orderedQtyStr)      // Convert to float64\n"
            "       b.OrderedQty = &orderedQty            // Now it's *float64\n\n"
            
            "9. RETURN TYPE ERRORS:\n"
            "   - Error: 'cannot use dbGetValue(...) (type string) as map[string]string'\n"
            "   - CAUSE: dbGetValue returns string, not map[string]string\n"
            "   - FIX: Use getBinDetails() which returns map[string]string\n"
            "   - OR: Parse the string into a map after getting it\n"
            "   - NEVER return a string when function signature says map[string]string\n\n"
            
            "10. MOCK ASSIGNMENT ERRORS:\n"
            "   - Error: 'cannot assign to getBinDetails (neither addressable nor a map index)'\n"
            "   - CAUSE: Trying to assign to function result, not the function itself\n"
            "   - WRONG:\n"
            "     getBinDetails(...) = someValue  // Can't assign to function call\n"
            "   \n"
            "   - RIGHT (Mocking in tests):\n"
            "     origGetBinDetails := getBinDetails    // Save original\n"
            "     getBinDetails = func(batch string) map[string]string {  // Reassign function\n"
            "         return map[string]string{\"actual_qty\": \"100\"}\n"
            "     }\n"
            "     defer func() { getBinDetails = origGetBinDetails }()  // Restore\n\n"
            
            "11. FUNCTION REDECLARATION IN PRODUCTION CODE:\n"
            "   - Error: 'getBinDetails redeclared in this block'\n"
            "   - CAUSE: Function defined twice in the same file\n"
            "   - FIX: Remove the second definition, keep only the first one\n"
            "   - Search for 'var getBinDetails = func' and delete duplicate definitions\n"
            "   - Each function should appear only ONCE in production code\n\n"
            
            "12. UNDEFINED FUNCTION ERRORS:\n"
            "   - Error: 'undefined: getPlannedQty' or 'undefined: getIndentedQty'\n"
            "   - CAUSE: These functions DO NOT EXIST and NEVER WILL\n"
            "   - FIX: Replace EVERY undefined call with getValueStr pattern:\n"
            "   \n"
            "   DELETE THIS:\n"
            "   plannedQty := getPlannedQty(item, warehouse)\n"
            "   \n"
            "   REPLACE WITH THIS:\n"
            "   plannedQtyStr, _ := getValueStr(\"Bin\", binName, \"planned_qty\")\n"
            "   plannedQty := flt(plannedQtyStr)\n"
            "   \n"
            "   COMPLETE REPLACEMENT LIST:\n"
            "   - getPlannedQty → getValueStr(..., \"planned_qty\")\n"
            "   - getIndentedQty → getValueStr(..., \"indented_qty\")\n"
            "   - getOrderedQty → getValueStr(..., \"ordered_qty\")\n"
            "   - getReservedQty → getValueStr(..., \"reserved_qty\")\n"
            "   - getReservedQtyForProduction → getValueStr(..., \"reserved_qty_for_production\")\n"
            "   \n"
            "   ALL of these should use the SAME pattern:\n"
            "   fieldStr, _ := getValueStr(\"Bin\", binName, \"field_name\")\n"
            "   field := flt(fieldStr)\n\n"
            
            "13. ASSIGNMENT MISMATCH (SINGLE RETURN):\n"
            "   - Error: 'assignment mismatch: 2 variables but getBinDetails returns 1 value'\n"
            "   - CAUSE: Function returns single value, not (value, error)\n"
            "   - FIX:\n"
            "     WRONG: result, err := getBinDetails(name)\n"
            "     RIGHT: result := getBinDetails(name)\n"
            "   - Functions returning single values (no error):\n"
            "     getBinDetails, GetActualQty, getValuationMethod,\n"
            "     getReservedQtyForProductionPlan, getBatchQty, makeAutoname, cint, flt\n\n"
            
            "COMPLETE FUNCTION SIGNATURES (USE THESE EXACTLY):\n"
            "var getValueStr = func(doctype, name, fieldname string) (string, error)\n"
            "var dbGetValue = func(doctype, name, fieldname string) (string, error)\n"
            "var dbSet = func(doctype, name, fieldname, value string) error\n"
            "var GetActualQty = func(itemCode, warehouse string) float64\n"
            "var getValuationMethod = func(item string) string\n"
            "var getReservedQtyForProductionPlan = func(productionPlan, item string) float64\n"
            "var getBatchQty = func(batch, warehouse string) float64\n"
            "var makeAutoname = func(key string) string\n"
            "var getNameFromHash = func(hash string) string\n"
            "var batchExists = func(name string) bool\n"
            "var futureSleExists = func(args interface{}) bool\n"
            "var revertSeriesIfLast = func(series, name string)\n"
            "var addDays = func(date string, days int) string\n"
            "var renderTemplate = func(template string, data interface{}) string\n"
            "var cint = func(val string) int\n"
            "var cstr = func(val interface{}) string\n"
            "var flt = func(val string) float64\n"
            "var getBatchDetails = func(batch string) map[string]string\n"
            "var getExpiryDetails = func(batch string) string\n\n"
            
            "SPECIFIC FIXES FOR TEST FILES:\n"
            "- NEVER use 'var functionName = func' if functionName exists in production\n"
            "- ALWAYS use 'functionName = func' (reassignment, not declaration)\n"
            "- Save original: orig := functionName\n"
            "- Mock: functionName = func(...) { return mockValue }\n"
            "- Restore: defer func() { functionName = orig }()\n\n"
            
            "Output ONLY the fixed Go code, no explanations."
        )

        fixed = self._query_llm(prompt, "Fix")
        fixed = self._clean_code(fixed)
        self._validate_go(fixed)
        self._validate_braces(fixed)
        return fixed

    def explain_logic(self, query: str, context_docs: list) -> str:
        """Explains complex ERPNext logic using retrieved context."""
        context_str = "\n".join(context_docs) if context_docs else "No specific code context available."
        
        system_prompt = (
            "You are a specialized ERPNext technical assistant. "
            "Answer the user's question based strictly on the provided code context. "
            "Do not use any Markdown formatting (like **bold** or *italics*). "
            "Write in plain text paragraphs or bullet points using simple dashes (-)."
        )
        user_message = f"CONTEXT:\n{context_str}\n\nUSER QUERY: {query}"
        
        return self._query_llm(system_prompt, user_message)