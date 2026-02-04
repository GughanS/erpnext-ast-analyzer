# Migration Report: issue_priority
**Status:** FAILED
**Date:** 2026-02-04 21:48:30

## Migration Log
- Started migration for issue_priority.py
- Initial code generated and saved.
- Verification Round 1 started.
- Round 1: FAILED. Errors detected.
- Attempting self-healing for Round 1 errors.
- Applied fixes to Test file.
- Verification Round 2 started.
- Round 2: FAILED. Errors detected.
- Attempting self-healing for Round 2 errors.
- Applied fixes to Test file.
- Verification Round 3 started.
- Round 3: FAILED. Errors detected.
- Max retries reached or error not fixable.

## Final Test Output
```text
FAIL	issue_priority [build failed]
# issue_priority [issue_priority.test]
.\issue_priority_test.go:9:21: undefined: getValueStr
.\issue_priority_test.go:12:2: undefined: getValueStr
.\issue_priority_test.go:18:3: undefined: getValueStr
.\issue_priority_test.go:22:16: undefined: getValueStr
.\issue_priority_test.go:33:22: undefined: GetActualQty
.\issue_priority_test.go:36:2: undefined: GetActualQty
.\issue_priority_test.go:42:3: undefined: GetActualQty
.\issue_priority_test.go:46:15: undefined: GetActualQty
.\issue_priority_test.go:54:41: undefined: getReservedQtyForProductionPlan
.\issue_priority_test.go:57:2: undefined: getReservedQtyForProductionPlan
.\issue_priority_test.go:57:2: too many errors

```
