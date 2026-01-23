"""
Example: Financial data validation for fintech use case
"""

from pyrustpipe import Validator, Schema, Field, validate

# Define schema for transaction data
transaction_schema = Schema({
    "transaction_id": Field(str, required=True, pattern=r"^TXN\d{10}$"),
    "user_id": Field(int, required=True, min=1),
    "amount": Field(float, required=True, min=0.01, max=1000000.0),
    "currency": Field(str, required=True, pattern=r"^[A-Z]{3}$"),
    "timestamp": Field(str, required=True),
    "status": Field(str, required=True),
    "merchant": Field(str, required=True, min_length=2, max_length=200),
})

# Custom business rules
@validate
def check_suspicious_amount(row):
    """Flag potentially suspicious transactions"""
    if row.amount > 50000:
        # In real implementation, this might trigger additional checks
        print(f"⚠️  Large transaction detected: {row.transaction_id} - ${row.amount}")
    return True

@validate
def check_valid_status(row):
    """Ensure status is valid"""
    valid_statuses = ["pending", "completed", "failed", "cancelled"]
    assert row.status.lower() in valid_statuses, f"Invalid status: {row.status}"

@validate
def check_currency_supported(row):
    """Ensure currency is supported"""
    supported = ["USD", "EUR", "GBP", "NGN", "ZAR", "KES"]
    assert row.currency in supported, f"Unsupported currency: {row.currency}"

# Create validator for fintech data
fintech_validator = Validator(
    schema=transaction_schema,
    rules=[check_suspicious_amount, check_valid_status, check_currency_supported],
    parallel=True,
    chunk_size=50000  # Process 50k transactions at a time
)

# Example usage
print("Financial Transaction Validator")
print("=" * 50)

# Test single transaction
test_transaction = {
    "transaction_id": "TXN0123456789",
    "user_id": 42,
    "amount": 250.75,
    "currency": "USD",
    "timestamp": "2026-01-19T10:30:00Z",
    "status": "completed",
    "merchant": "Online Store XYZ"
}

errors = fintech_validator.validate_dict(test_transaction)
if errors:
    print("❌ Transaction validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✓ Transaction is valid")

# For production: validate large CSV files from S3
# result = fintech_validator.validate_s3(
#     bucket="fintech-transactions",
#     key="2026/01/transactions.csv",
#     output_bucket="validation-results",
#     output_key="2026/01/validation_report.json"
# )
# print(result.summary())
