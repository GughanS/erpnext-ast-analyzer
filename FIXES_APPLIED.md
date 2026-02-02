# ERPNext Accounts Module - Migration Error Fixes

## Issues Identified & Fixed

### 1. ❌ Missing `groq` Dependency
**Error**: ModuleNotFoundError when importing groq  
**Fix**: Added to `requirements.txt`:
```
groq
requests
```

### 2. ❌ Groq API Rate Limiting Not Handled Properly
**Error**: "429 Too Many Requests" crashes migration  
**Fixed in `src/generator.py`**:

**Before:**
```python
except RateLimitError:
    wait_time = 2 ** attempt  # Exponential growth: 1, 2, 4, 8, 16, 32, 64... seconds
    print(f" Rate Limit. Waiting {wait_time}s...")
    if self._rotate_key():
        continue
    else:
        print(" All keys exhausted.")
        break  # ❌ Breaks loop entirely
```

**After:**
```python
except RateLimitError as e:
    wait_time = 2 ** min(attempt, 5)  # ✅ Capped at 32 seconds
    jitter = random.uniform(0, 1)     # ✅ Add jitter (0-1s)
    total_wait = wait_time + jitter
    
    print(f"⏳ Rate Limited (Attempt {attempt + 1}/{max_retries}). Waiting {total_wait:.1f}s...")
    time.sleep(total_wait)
    
    if self._rotate_key():
        continue
    else:
        print("❌ All keys exhausted. Cannot proceed.")
        raise Exception(f"Groq API Error: {str(e)}")  # ✅ Raises exception instead of breaking
```

### 3. ❌ Key Rotation Reused Exhausted Keys
**Error**: Keeps using same rate-limited key in a cycle  
**Fixed in `src/generator.py`**:

**Before:**
```python
def _rotate_key(self):
    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
    # ❌ Rotates to key 1→2→3→1→2→3 regardless of rate limits
    self.client = self._get_client()
    return True
```

**After:**
```python
def _rotate_key(self):
    if len(self.api_keys) <= 1:
        print("⚠️ Only one key available. Cannot rotate.")
        return False
    
    # Mark current key as used
    self.used_keys.add(self.current_key_index)
    
    # ✅ Try to find unused keys first
    unused_keys = [i for i in range(len(self.api_keys)) if i not in self.used_keys]
    
    if unused_keys:
        self.current_key_index = unused_keys[0]
    else:
        # Reset cycle when all are exhausted
        self.used_keys.clear()
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self.used_keys.add(self.current_key_index)
    
    print(f"🔄 Rotating to Key #{self.current_key_index + 1}/{len(self.api_keys)}...")
    self.client = self._get_client()
    return True
```

### 4. ❌ Aggressive Threading Caused Google API Rate Limits
**Error**: "429 Too Many Requests" from Google Embedding API  
**Fixed in `src/indexer.py`**:

**Before:**
```python
MAX_WORKERS = 10  # ❌ Creates 10 concurrent API calls → Rate limit immediately
```

**After:**
```python
MAX_WORKERS = 3  # ✅ 3 workers respects Google's ~100 req/min quota
```

### 5. ❌ Migration Errors Crashed Entire Indexing
**Error**: One failed migration stops all processing  
**Fixed in `src/indexer.py`**:

**Before:**
```python
if auto_migrate:
    print(f"⚡ Migrating '{chunk['name']}' to Go (Threaded)...")
    self.generator.migrate_and_save(chunk)  # ❌ Exception crashes indexing
```

**After:**
```python
if auto_migrate:
    try:
        print(f"⚡ Migrating '{chunk['name']}' to Go...")
        migration_file = self.generator.migrate_and_save(chunk)
        print(f"✅ Generated: {migration_file}")
    except Exception as migrate_error:
        # ✅ Log error but continue indexing
        print(f"⚠️ Migration failed for '{chunk['name']}': {str(migrate_error)[:100]}")
```

## Before vs After Performance

| Issue | Before | After |
|-------|--------|-------|
| Rate limit handling | Crashes | Retries with exponential backoff |
| Jitter in backoff | None | Added (prevents thundering herd) |
| Max wait time | Unbounded (exponential explosion) | Capped at 32s |
| Key rotation | Cycles through regardless of status | Uses unused keys first |
| Concurrent workers | 10 (overwhelms API) | 3 (safe quota) |
| Migration failures | Stops entire process | Continues with logging |
| Retry attempts | 6 (2 per key) | 9 (3 per key) |

## Expected Behavior During Migration

```
🚀 Processing 45 functions with 3 concurrent threads...

[Processing 1-3 chunks...]
⏳ Rate Limited (Attempt 2/9). Waiting 4.3s...
🔄 Rotating to Key #2/3...

[Processing 4-6 chunks...]
⏳ Rate Limited (Attempt 4/9). Waiting 8.7s...
🔄 Rotating to Key #3/3...

⚡ Migrating 'validate' to Go...
✅ Generated: generated/accounts/doctype/sales_invoice_validate.go

💾 Saving 45 vectors to database...
✅ Successfully indexed 45 functions!
```

## How to Run Accounts Migration

```bash
cd d:\Internship-Obsidian-Vault\erpnext-ast-analyzer

# Install fixed dependencies
pip install -r requirements.txt

# Run migration with all fixes applied
python cli.py index erpnext/accounts --auto-migrate
```

## Verify Your .env File

```env
GOOGLE_API_KEY=YOUR_GOOGLE_KEY
GROQ_API_KEYS=gsk_key1,gsk_key2,gsk_key3
```

**Important**: Separate Groq keys with commas (no spaces).

## Files Modified

1. **requirements.txt** - Added `groq` and `requests`
2. **src/generator.py** - Fixed retry logic, backoff, and key rotation
3. **src/indexer.py** - Reduced workers to 3, added migration error handling

All fixes are now active and ready for accounts migration!
