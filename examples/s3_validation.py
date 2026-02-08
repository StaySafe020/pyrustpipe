"""
Example: Validate CSV data directly from AWS S3
================================================

This example demonstrates how to:
1. Validate a CSV file stored in S3
2. Track progress during validation
3. Upload validation results back to S3

Requirements:
    pip install boto3

AWS credentials:
    Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION environment variables,
    or configure ~/.aws/credentials
"""

from pyrustpipe import Schema, Field, S3Validator

# Define validation schema
schema = Schema({
    'transaction_id': Field(str, required=True),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'amount': Field(float, required=True, min=0.01, max=1_000_000),
    'currency': Field(str, required=True, choices=['USD', 'EUR', 'GBP', 'KES', 'NGN', 'ZAR']),
    'timestamp': Field(str, required=True),
})


def progress_callback(info):
    """Print validation progress."""
    print(f"  Chunk {info['chunk']}/{info['total_chunks']} - "
          f"Valid: {info['valid_so_far']}, Invalid: {info['invalid_so_far']} "
          f"({info['progress_pct']:.1f}%)")


def main():
    # Configuration
    BUCKET = 'your-data-bucket'
    KEY = 'transactions/2026-01-31.csv'
    RESULTS_KEY = 'validation-results/2026-01-31.json'
    
    print(f"\n🔍 Validating s3://{BUCKET}/{KEY}...\n")
    
    # Create S3 validator with 4 parallel workers
    validator = S3Validator(
        schema=schema,
        workers=4,
        chunk_size=10000
    )
    
    # Validate with progress tracking
    result = validator.validate(
        bucket=BUCKET,
        key=KEY,
        callback=progress_callback
    )
    
    print(f"\n✅ Validation Complete!")
    print(f"   Total rows: {result.total_rows:,}")
    print(f"   Valid: {result.valid_count:,}")
    print(f"   Invalid: {result.invalid_count:,}")
    print(f"   Success rate: {result.success_rate():.2f}%")
    
    # Upload results to S3
    if result.invalid_count > 0:
        results_uri = validator.upload_results(
            result=result,
            bucket=BUCKET,
            key=RESULTS_KEY
        )
        print(f"\n📤 Results uploaded to: {results_uri}")
    
    return result


# For streaming large files (memory-efficient)
def validate_large_file():
    """Use streaming validation for files larger than available RAM."""
    
    validator = S3Validator(
        schema=schema,
        workers=4,
        chunk_size=50000
    )
    
    result = validator.validate_streaming(
        bucket='your-bucket',
        key='huge-file.csv',
        callback=progress_callback
    )
    
    print(f"Validated {result.total_rows:,} rows using streaming")
    return result


if __name__ == '__main__':
    # Note: This requires valid AWS credentials and an actual S3 bucket
    # For testing without S3, see examples/basic_validation.py
    
    print("=" * 60)
    print("PyRustPipe S3 Validation Example")
    print("=" * 60)
    print("\nNote: This example requires:")
    print("  1. boto3 installed (pip install boto3)")
    print("  2. AWS credentials configured")
    print("  3. An actual S3 bucket with CSV data")
    print("\nTo run a local demo instead, use:")
    print("  python demo_code.py")
    print("  python performance_demo.py")
    print("=" * 60)
    
    # Uncomment to run:
    # main()
