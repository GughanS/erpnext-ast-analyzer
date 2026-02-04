# Migration Report: bin
**Status:** FAILED
**Date:** 2026-02-04 21:38:58

## Migration Log
- Started migration for bin.py
- Initial code generated and saved.
- Verification Round 1 started.
- Round 1: FAILED. Errors detected.
- Attempting self-healing for Round 1 errors.
- Applied fixes to Implementation file.
- Verification Round 2 started.
- Round 2: FAILED. Errors detected.
- Attempting self-healing for Round 2 errors.
- Applied fixes to Implementation file.
- Verification Round 3 started.
- Round 3: FAILED. Errors detected.
- Max retries reached or error not fixable.

## Final Test Output
```text
FAIL	bin [build failed]
# bin [bin.test]
.\bin.go:104:2: declared and not used: plannedQtyStr
.\bin.go:107:2: declared and not used: indentedQtyStr
.\bin.go:110:2: declared and not used: orderedQtyStr
.\bin.go:113:2: declared and not used: reservedQtyStr
.\bin.go:116:2: declared and not used: reservedQtyForProductionStr
.\bin.go:125:18: b.StockUOM undefined (type *Bin has no field or method StockUOM)
.\bin.go:127:5: b.StockUOM undefined (type *Bin has no field or method StockUOM)
.\bin.go:133:2: declared and not used: total
.\bin.go:140:45: b.ReservedQtyForProductionPlan undefined (type *Bin has no field or method ReservedQtyForProductionPlan)
.\bin.go:144:4: b.ReservedQtyForProductionPlan undefined (type *Bin has no field or method ReservedQtyForProductionPlan)
.\bin.go:144:4: too many errors

```
