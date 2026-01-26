# How to Use PyRustPipe for Large Data Processing

## 🎯 Quick Start Guide

This guide shows you how to use pyrustpipe to validate large datasets, from thousands to billions of records.

---

## 📦 Installation

```bash
# Clone the repository
git clone REPO LINK
cd pyrustpipe

# Install dependencies
pip install -e .

# Build Rust backend
maturin develop --release
```

---

## 🚀 Usage Options

You have **3 ways** to use pyrustpipe:

### Option 1: CLI Tool (Simplest - No Coding)
### Option 2: Python Script (Most Flexible)
### Option 3: Integration in Your Pipeline (Production)

---

## 📋 Option 1: CLI Tool (No Coding Required)

Perfect for: Quick validation, one-off jobs, testing

### Step 1: Create Your Rules File

```bash
# Generate template
pyrustpipe init --output my_rules.py
```

This creates `my_rules.py`:
```python
from pyrustpipe import Schema, Field

# Define your validation rules here
schema = Schema({
    'user_id': Field(str, required=True),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, min=18, max=120),
    'balance': Field(float, min=0.0)
})
```

### Step 2: Edit Rules for Your Data

```python
# Example: E-commerce orders
schema = Schema({
    'order_id': Field(str, required=True, pattern=r'^ORD\d{8}$'),
    'customer_email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'amount': Field(float, required=True, min=0.01, max=1000000.0),
    'status': Field(str, required=True, pattern=r'^(pending|completed|cancelled)$'),
    'created_at': Field(str, required=True)
})
```

### Step 3: Validate Your Data

```bash
# Validate a CSV file
pyrustpipe validate data.csv --schema my_rules.py

# Output:
# ✓ Validated 1,000,000 rows in 3.2 seconds
# Valid: 985,432 (98.5%)
# Invalid: 14,568 (1.5%)
# Results saved to: validation_results.json
```

### Step 4: View Results

```bash
# View summary
cat validation_results.json | jq '.summary'

# View errors only
cat validation_results.json | jq '.errors[] | select(.field == "email")'
```

---

## 💻 Option 2: Python Script (Most Common)

Perfect for: Custom workflows, automation, integration

### Small to Medium Data (< 1 GB)

```python
from pyrustpipe import Validator, Schema, Field

# Define rules
schema = Schema({
    'transaction_id': Field(str, required=True),
    'amount': Field(float, min=0.0),
    'email': Field(str, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
})

# Create validator with parallel processing
validator = Validator(schema=schema, parallel=True)

# Validate CSV file
result = validator.validate_csv('transactions.csv')

# Check results
print(f"Total rows: {result.total_rows:,}")
print(f"Valid: {result.valid_count:,} ({result.success_rate():.1f}%)")
print(f"Invalid: {result.invalid_count:,}")

# Show errors
if result.invalid_count > 0:
    print("\nFirst 10 errors:")
    for error in result.errors[:10]:
        print(f"  Row {error.row_index}: {error.field} - {error.message}")
```

### Large Data (1-10 GB) - Use Streaming

```python
from pyrustpipe import StreamingValidator, Schema, Field

schema = Schema({
    'id': Field(str, required=True),
    'value': Field(float, min=0.0)
})

# Streaming validator - uses only ~100 MB memory
validator = StreamingValidator(
    schema=schema,
    buffer_size=10000,  # Process 10K rows at a time
    parallel=True
)

# Process file in batches
total_valid = 0
total_invalid = 0

print("Processing large file...")
for batch_num, result in enumerate(validator.validate_csv_stream('huge_file.csv'), 1):
    total_valid += result.valid_count
    total_invalid += result.invalid_count
    
    # Progress update every 10 batches
    if batch_num % 10 == 0:
        total = total_valid + total_invalid
        print(f"  Processed {total:,} rows... ({total_valid/total*100:.1f}% valid)")

print(f"\n✓ Completed!")
print(f"Valid: {total_valid:,}")
print(f"Invalid: {total_invalid:,}")
```

### Very Large Data (10+ GB) - Use Distributed

```python
from pyrustpipe import DistributedValidator, Schema, Field
import time

schema = Schema({
    'id': Field(str, required=True),
    'amount': Field(float, min=0.0)
})

# Distributed validator - uses multiple CPU cores
validator = DistributedValidator(
    schema=schema,
    workers=8,  # Use 8 CPU cores
    chunk_size=50000  # 50K rows per chunk
)

# Progress callback
def show_progress(info):
    pct = (info['chunk'] / info['total_chunks']) * 100
    print(f"  Progress: {pct:.1f}% - Valid: {info['valid_so_far']:,}, Invalid: {info['invalid_so_far']:,}")

# Validate with progress tracking
print("Starting distributed validation...")
start = time.time()

result = validator.validate_csv_parallel('very_large_file.csv', callback=show_progress)

elapsed = time.time() - start
throughput = result.total_rows / elapsed

print(f"\n✓ Validation completed!")
print(f"Total rows: {result.total_rows:,}")
print(f"Time: {elapsed:.1f} seconds")
print(f"Throughput: {throughput:,.0f} rows/second")
print(f"Valid: {result.valid_count:,} ({result.success_rate():.1f}%)")
```

### Billion+ Records - Streaming + Caching

```python
from pyrustpipe import StreamingValidator, CachedValidator, Validator, Schema, Field
import time

schema = Schema({
    'id': Field(str, required=True),
    'timestamp': Field(str, required=True),
    'value': Field(float, min=0.0, max=999999.99)
})

# Use caching to avoid re-validating identical files
base_validator = Validator(schema=schema, parallel=True)
cached_validator = CachedValidator(base_validator, cache_dir='.validation_cache')

# Streaming for memory efficiency
streaming = StreamingValidator(schema=schema, buffer_size=50000, parallel=True)

print("Validating billion-record file...")
start = time.time()

# Check cache first
if cached_validator.cache.has_result('billion_records.csv'):
    print("✓ Using cached result (instant!)")
    result = cached_validator.cache.load_result('billion_records.csv')
else:
    print("Processing file (first time)...")
    total_valid = 0
    total_invalid = 0
    total_rows = 0
    
    for batch_num, result in enumerate(streaming.validate_csv_stream('billion_records.csv'), 1):
        total_valid += result.valid_count
        total_invalid += result.invalid_count
        total_rows += result.total_rows
        
        if batch_num % 100 == 0:
            elapsed = time.time() - start
            throughput = total_rows / elapsed
            eta_minutes = (1_000_000_000 - total_rows) / throughput / 60
            print(f"  {total_rows:,} rows | {throughput:,.0f} rows/sec | ETA: {eta_minutes:.1f} min")

elapsed = time.time() - start
print(f"\n✓ Completed in {elapsed/60:.1f} minutes")
print(f"Throughput: {total_rows/elapsed:,.0f} rows/second")
```

---

## 🏭 Option 3: Production Pipeline Integration

### Scenario 1: Daily Batch Job

```python
#!/usr/bin/env python3
"""
Daily data validation job
Run with: python daily_validation.py
"""

from pyrustpipe import StreamingValidator, Schema, Field
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define schema
schema = Schema({
    'transaction_id': Field(str, required=True),
    'amount': Field(float, min=0.01, max=1000000.0),
    'customer_id': Field(str, required=True, pattern=r'^CUST\d{8}$')
})

def validate_daily_file(date_str):
    """Validate file for specific date"""
    input_file = f"/data/raw/transactions_{date_str}.csv"
    output_file = f"/data/validated/transactions_{date_str}_results.json"
    
    logger.info(f"Validating {input_file}...")
    
    # Use streaming for efficiency
    validator = StreamingValidator(schema=schema, buffer_size=10000)
    
    total_valid = 0
    total_invalid = 0
    all_errors = []
    
    for result in validator.validate_csv_stream(input_file):
        total_valid += result.valid_count
        total_invalid += result.invalid_count
        all_errors.extend(result.errors)
    
    # Save results
    import json
    with open(output_file, 'w') as f:
        json.dump({
            'date': date_str,
            'total_rows': total_valid + total_invalid,
            'valid_count': total_valid,
            'invalid_count': total_invalid,
            'success_rate': (total_valid / (total_valid + total_invalid)) * 100,
            'error_count': len(all_errors)
        }, f, indent=2)
    
    logger.info(f"✓ Results saved to {output_file}")
    
    # Alert if too many errors
    if total_invalid > 1000:
        logger.warning(f"High error count: {total_invalid} invalid rows!")
        # Send alert (email, Slack, etc.)
    
    return total_valid, total_invalid

if __name__ == '__main__':
    today = datetime.now().strftime('%Y%m%d')
    validate_daily_file(today)
```

### Scenario 2: Real-time Stream Processing

```python
"""
Real-time validation for streaming data
Use with Kafka, Kinesis, or any message queue
"""

from pyrustpipe import LineProcessor, Schema, Field
import json

# Define schema
schema = Schema({
    'event_id': Field(str, required=True),
    'user_id': Field(str, required=True),
    'event_type': Field(str, required=True),
    'timestamp': Field(str, required=True)
})

# Create line processor (minimal overhead)
processor = LineProcessor(schema=schema)

def process_message(message):
    """Process single message from queue"""
    try:
        data = json.loads(message)
        
        # Validate instantly
        is_valid, errors = processor.process_line(data)
        
        if is_valid:
            # Send to valid queue
            send_to_valid_queue(data)
        else:
            # Send to dead letter queue
            send_to_dlq(data, errors)
            log_validation_error(data, errors)
        
    except Exception as e:
        log_error(f"Failed to process message: {e}")

# Kafka consumer example
def consume_kafka():
    from kafka import KafkaConsumer
    
    consumer = KafkaConsumer('raw-events', 
                            bootstrap_servers=['localhost:9092'])
    
    for message in consumer:
        process_message(message.value)
```

### Scenario 3: AWS Lambda Function

```python
"""
AWS Lambda function for S3-triggered validation
Deploy with: serverless deploy
"""

import json
from pyrustpipe import Validator, Schema, Field

# Define schema (outside handler for reuse)
schema = Schema({
    'order_id': Field(str, required=True),
    'amount': Field(float, min=0.0)
})

validator = Validator(schema=schema, parallel=True)

def lambda_handler(event, context):
    """
    Triggered when file uploaded to S3
    """
    # Get S3 info from event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    print(f"Validating s3://{bucket}/{key}")
    
    # Validate S3 file
    result = validator.validate_s3(
        bucket=bucket,
        key=key,
        output_bucket=bucket,
        output_key=key.replace('.csv', '_validation.json')
    )
    
    # Return results
    return {
        'statusCode': 200,
        'body': json.dumps({
            'total_rows': result.total_rows,
            'valid_count': result.valid_count,
            'invalid_count': result.invalid_count,
            'success_rate': result.success_rate()
        })
    }
```

### Scenario 4: CI/CD Pipeline

```yaml
# .github/workflows/validate-data.yml
name: Validate Test Data

on:
  push:
    paths:
      - 'data/test/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install pyrustpipe
      run: |
        pip install -e .
        maturin develop --release
    
    - name: Validate test data
      run: |
        pyrustpipe validate data/test/sample.csv --schema rules/test_schema.py
    
    - name: Check results
      run: |
        python -c "
        import json
        with open('validation_results.json') as f:
            result = json.load(f)
        if result['invalid_count'] > 0:
            print(f\"❌ Validation failed: {result['invalid_count']} errors\")
            exit(1)
        print(f\"✅ All {result['total_rows']} rows valid\")
        "
```

---

## 📊 Performance Guide by Data Size

| Data Size | Method | Expected Time | Memory | Command |
|-----------|--------|---------------|--------|---------|
| **< 100 MB** | Standard | 1-2 seconds | < 100 MB | `validator.validate_csv()` |
| **100 MB - 1 GB** | Parallel | 5-10 seconds | < 500 MB | `Validator(parallel=True)` |
| **1-10 GB** | Streaming | 1-5 minutes | < 100 MB | `StreamingValidator` |
| **10-100 GB** | Distributed | 2-10 minutes | < 1 GB | `DistributedValidator(workers=8)` |
| **100+ GB** | Distributed | 10-30 minutes | < 2 GB | `DistributedValidator(workers=32)` |
| **1 TB+** | MapReduce | 1-2 hours | Distributed | Use Spark/Ray integration |

---

## 🎯 Common Use Cases

### Use Case 1: Financial Transactions
```python
schema = Schema({
    'transaction_id': Field(str, required=True, pattern=r'^TXN\d{10}$'),
    'account_from': Field(str, required=True, min_length=8, max_length=20),
    'account_to': Field(str, required=True, min_length=8, max_length=20),
    'amount': Field(float, required=True, min=0.01, max=1000000.0),
    'currency': Field(str, required=True, pattern=r'^(USD|EUR|GBP)$'),
    'timestamp': Field(str, required=True)
})
```

### Use Case 2: User Registrations
```python
schema = Schema({
    'user_id': Field(str, required=True, pattern=r'^USR\d{8}$'),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'phone': Field(str, pattern=r'^\+?1?\d{9,15}$'),
    'age': Field(int, min=18, max=120),
    'country': Field(str, required=True, min_length=2, max_length=2)
})
```

### Use Case 3: IoT Sensor Data
```python
schema = Schema({
    'device_id': Field(str, required=True, pattern=r'^DEV\d{6}$'),
    'sensor_type': Field(str, required=True, pattern=r'^(temperature|humidity|pressure)$'),
    'value': Field(float, required=True, min=-50.0, max=150.0),
    'timestamp': Field(str, required=True),
    'location': Field(str, required=True)
})
```

### Use Case 4: E-commerce Orders
```python
schema = Schema({
    'order_id': Field(str, required=True, pattern=r'^ORD\d{8}$'),
    'customer_email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'product_id': Field(str, required=True, pattern=r'^PRD\d{6}$'),
    'quantity': Field(int, required=True, min=1, max=1000),
    'price': Field(float, required=True, min=0.01, max=100000.0),
    'status': Field(str, required=True, pattern=r'^(pending|paid|shipped|delivered)$')
})
```

---

## 🔧 Advanced Configuration

### Custom Validation Rules

```python
from pyrustpipe import Schema, Field, rule

# Define custom rule
@rule
def is_business_email(value):
    """Only allow business emails"""
    blocked_domains = ['gmail.com', 'yahoo.com', 'hotmail.com']
    domain = value.split('@')[1] if '@' in value else ''
    return domain not in blocked_domains, f"Personal email not allowed: {domain}"

# Use in schema
schema = Schema({
    'email': Field(str, required=True, validators=[is_business_email])
})
```

### Error Handling

```python
from pyrustpipe import Validator, Schema, Field

validator = Validator(schema=schema)

try:
    result = validator.validate_csv('data.csv')
    
    if result.invalid_count > 0:
        # Save errors to file
        with open('errors.txt', 'w') as f:
            for error in result.errors:
                f.write(f"Row {error.row_index}: {error.field} - {error.message}\n")
        
        print(f"❌ Found {result.invalid_count} errors. See errors.txt")
    else:
        print(f"✅ All {result.total_rows} rows valid!")
        
except FileNotFoundError:
    print("Error: File not found")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## 📞 Support

**Documentation**: See `/docs` folder
**Examples**: See `/examples` folder
**Issues**: GitHub Issues
**Performance Tips**: See `ADVANCED_FEATURES.md`

---

## 🚀 Quick Reference

```bash
# CLI commands
pyrustpipe init --output rules.py          # Create rules template
pyrustpipe validate data.csv --schema rules.py  # Validate file
pyrustpipe --help                          # Show all commands

# Python quick validation
python -c "from pyrustpipe import Validator, Schema, Field; \
  schema = Schema({'id': Field(str)}); \
  v = Validator(schema=schema); \
  print(v.validate_csv('data.csv').summary())"
```

---

**Ready to process billions of records?** Pick the method that fits your needs and start validating! 
