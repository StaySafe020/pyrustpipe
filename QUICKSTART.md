# Quick Start Guide

Get started with pyrustpipe in 5 minutes!

## Installation

```bash
pip install pyrustpipe
```

## Basic Usage

### 1. Define Validation Rules

```python
from pyrustpipe import Schema, Field, Validator

# Create a schema
user_schema = Schema({
    "name": Field(str, required=True, min_length=2),
    "email": Field(str, required=True, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "age": Field(int, required=True, min=18, max=120),
    "balance": Field(float, min=0.0)
})

# Create validator
validator = Validator(schema=user_schema, parallel=True)
```

### 2. Validate Data

**Single Dictionary:**

```python
data = {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 25,
    "balance": 1000.50
}

errors = validator.validate_dict(data)
if errors:
    print("Invalid:", errors)
else:
    print("Valid!")
```

**CSV File:**

```python
result = validator.validate_csv("users.csv")
print(f"Valid: {result.valid_count}/{result.total_rows}")
print(f"Success rate: {result.success_rate():.2f}%")
```

**AWS S3:**

```python
result = validator.validate_s3(
    bucket="my-bucket",
    key="data/users.csv"
)
print(result.summary())
```

## Custom Validation Rules

Use decorators for custom logic:

```python
from pyrustpipe import validate

@validate
def check_age_consistency(row):
    """Ensure age matches birth year"""
    current_year = 2026
    expected_age = current_year - row.birth_year
    assert abs(row.age - expected_age) <= 1, "Age doesn't match birth year"

validator = Validator(rules=[check_age_consistency])
```

## CLI Usage

### Initialize Rules File

```bash
pyrustpipe init my_rules.py --name=my_validation
```

### Run Validation

```bash
# Local file
pyrustpipe validate --rules my_rules.py --input data.csv

# S3 file
pyrustpipe validate --rules my_rules.py --s3 s3://bucket/data.csv

# With custom options
pyrustpipe validate \
    --rules my_rules.py \
    --input data.csv \
    --output results.json \
    --parallel \
    --chunk-size 50000 \
    --verbose
```

## Common Patterns

### Fintech Validation

```python
from pyrustpipe import Schema, Field, validate

transaction_schema = Schema({
    "txn_id": Field(str, required=True, pattern=r"^TXN\d{10}$"),
    "amount": Field(float, required=True, min=0.01, max=1000000.0),
    "currency": Field(str, required=True, pattern=r"^[A-Z]{3}$"),
    "status": Field(str, required=True)
})

@validate
def check_status(row):
    valid = ["pending", "completed", "failed"]
    assert row.status in valid, f"Invalid status: {row.status}"

@validate
def flag_large_amount(row):
    if row.amount > 50000:
        print(f"⚠️  Large transaction: {row.txn_id} - ${row.amount}")
    return True

validator = Validator(
    schema=transaction_schema,
    rules=[check_status, flag_large_amount]
)
```

### ETL Pipeline Validation

```python
# In your ETL script
from pyrustpipe import Validator, Schema, Field

# Define expected schema
schema = Schema({
    "id": Field(int, required=True),
    "timestamp": Field(str, required=True),
    "value": Field(float, required=True)
})

validator = Validator(schema=schema, parallel=True)

# Validate extracted data
result = validator.validate_csv("extracted_data.csv")

if result.invalid_count > 0:
    print(f"❌ Validation failed: {result.invalid_count} invalid rows")
    for error in result.errors[:10]:  # Show first 10 errors
        print(f"  Row {error.row_index}: {error.message}")
    exit(1)
else:
    print("✅ All data valid, proceeding with transformation...")
```

### Data Quality Monitoring

```python
import schedule
from pyrustpipe import Validator, Schema, Field

schema = Schema({
    "metric": Field(str, required=True),
    "value": Field(float, required=True),
    "timestamp": Field(str, required=True)
})

validator = Validator(schema=schema)

def validate_daily_data():
    result = validator.validate_s3(
        bucket="metrics-bucket",
        key="daily/metrics.csv"
    )
    
    if result.success_rate() < 95:
        send_alert(f"Data quality below threshold: {result.success_rate():.2f}%")

# Run daily at 2 AM
schedule.every().day.at("02:00").do(validate_daily_data)
```

## Performance Tips

1. **Use Parallel Processing**: Set `parallel=True` (default)
2. **Tune Chunk Size**: Larger chunks = less overhead, more memory
3. **Schema Validation First**: Faster than custom Python rules
4. **Stream Large Files**: Don't load entire file into memory

## Error Handling

```python
from pyrustpipe import Validator
from pyrustpipe.types import ValidationError

try:
    result = validator.validate_csv("data.csv")
    
    if result.invalid_count > 0:
        # Get errors for specific field
        email_errors = result.get_errors_by_field("email")
        
        # Get errors for specific rule
        required_errors = result.get_errors_by_rule("email_required")
        
        # Save detailed report
        with open("validation_errors.json", "w") as f:
            json.dump([
                {
                    "row": e.row_index,
                    "field": e.field,
                    "message": e.message
                }
                for e in result.errors
            ], f, indent=2)
            
except Exception as e:
    print(f"Validation failed: {e}")
```

## Next Steps

- Read the [full documentation](https://pyrustpipe.readthedocs.io)
- Check out [more examples](https://github.com/yourusername/pyrustpipe/tree/main/examples)
- Join the [community discussions](https://github.com/yourusername/pyrustpipe/discussions)

## Need Help?

- 📖 [Full Documentation](https://pyrustpipe.readthedocs.io)
- 💬 [GitHub Discussions](https://github.com/yourusername/pyrustpipe/discussions)
- 🐛 [Report Issues](https://github.com/yourusername/pyrustpipe/issues)
- 📧 Email: your.email@example.com
