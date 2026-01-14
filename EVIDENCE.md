# Tool Effectiveness Evidence

## Experiment 1: Logic Extraction vs. Implementation Detail

**Question:** "What exact conditions must be met for a Sales Invoice to update the Stock Ledger?"

## My Tool (RAG)

**Context Retrieved:** sales_invoice.py lines 473-500.
Key Finding:

"**To update the Stock Ledger...**    
5. The "update_prevdoc_status" method must have been called before updating the Stock Ledger."

## ChatGPT (GPT-4o)

**Answer:**

"A Sales Invoice updates the Stock Ledger if and only if it is submitted and stock update is enabled... and it contains stock items..."

## Conclusion

While ChatGPT correctly identified the business rules (checked flags), it completely missed the implementation dependencies.

The Critical Miss:
My tool identified that update_prevdoc_status() MUST be called before the stock update logic. ChatGPT treated these as independent events.

Impact:
If a developer used ChatGPT's advice to write the new Go service, they would likely miss this mandatory method call order. This would cause data inconsistencies (orphaned documents) in the new system. My tool ensures the order of operations is preserved during migration.