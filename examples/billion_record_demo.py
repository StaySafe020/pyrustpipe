"""
Example: Billion-record processing with pyrustpipe

This example demonstrates how to efficiently validate massive datasets
using streaming, distributed, and cached validation.
"""

import time
import csv
import tempfile
from pathlib import Path
from pyrustpipe import (
    Schema, Field, 
    StreamingValidator, 
    DistributedValidator,
    CachedValidator,
    Validator
)


def generate_large_test_file(filepath: str, num_rows: int = 1_000_000):
    """Generate a large CSV file for testing."""
    print(f"Generating test file with {num_rows:,} rows...")
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'email', 'age', 'balance'])
        writer.writeheader()
        
        for i in range(num_rows):
            writer.writerow({
                'id': str(i),
                'name': f'User_{i}',
                'email': f'user{i}@example.com',
                'age': str(25 + (i % 50)),
                'balance': f'{1000 + (i * 0.5):.2f}'
            })
    
    print(f"✓ File generated: {Path(filepath).stat().st_size / (1024**2):.2f} MB")


def example_streaming_validation():
    """Example 1: Streaming validation for memory efficiency."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Streaming Validation (Memory Efficient)")
    print("="*70)
    
    # Define schema
    schema = Schema({
        'id': Field(str, required=True),
        'name': Field(str, required=True, min_length=2),
        'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
        'age': Field(str, required=True),
        'balance': Field(str, required=True),
    })
    
    # Generate test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    generate_large_test_file(test_file, num_rows=500_000)
    
    # Create streaming validator
    streaming_validator = StreamingValidator(
        schema=schema,
        buffer_size=10000,  # Process 10k rows at a time
        parallel=True
    )
    
    # Estimate memory usage
    file_size_gb = Path(test_file).stat().st_size / (1024**3)
    memory_info = streaming_validator.estimate_memory_usage(file_size_gb)
    
    print(f"\nMemory Estimate:")
    print(f"  File Size: {memory_info['file_size_gb']:.3f} GB")
    print(f"  Estimated Rows: {memory_info['estimated_rows']:,}")
    print(f"  Buffer Memory: {memory_info['buffer_memory_mb']:.2f} MB")
    print(f"  Batches: {memory_info['batches_required']}")
    
    # Validate in streaming mode
    print("\nValidating...")
    start = time.time()
    
    total_valid = 0
    total_invalid = 0
    total_rows = 0
    batch_count = 0
    
    for result in streaming_validator.validate_csv_stream(test_file):
        total_valid += result.valid_count
        total_invalid += result.invalid_count
        total_rows += result.total_rows
        batch_count += 1
        
        if batch_count % 10 == 0:
            print(f"  Processed {total_rows:,} rows ({batch_count} batches)...", end='\r')
    
    elapsed = time.time() - start
    throughput = total_rows / elapsed
    
    print(f"\n\n✓ Streaming validation completed!")
    print(f"  Total Rows: {total_rows:,}")
    print(f"  Valid: {total_valid:,}")
    print(f"  Invalid: {total_invalid:,}")
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  Throughput: {throughput:,.0f} rows/second")
    
    Path(test_file).unlink()


def example_distributed_validation():
    """Example 2: Distributed validation for maximum speed."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Distributed Validation (Multi-Core)")
    print("="*70)
    
    schema = Schema({
        'id': Field(str, required=True),
        'name': Field(str, required=True, min_length=2),
        'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
        'age': Field(str, required=True),
        'balance': Field(str, required=True),
    })
    
    # Generate test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    generate_large_test_file(test_file, num_rows=500_000)
    
    # Create distributed validator
    distributed_validator = DistributedValidator(
        schema=schema,
        workers=8,  # Use 8 parallel workers
        chunk_size=50000,  # 50k rows per chunk
        use_processes=False  # Use threads (faster for I/O bound)
    )
    
    # Get parallelization info
    file_size_gb = Path(test_file).stat().st_size / (1024**3)
    parallel_info = distributed_validator.get_parallelization_info(file_size_gb)
    
    print(f"\nParallelization Plan:")
    print(f"  Workers: {parallel_info['worker_threads']}")
    print(f"  Chunk Size: {parallel_info['chunk_size']:,}")
    print(f"  Total Chunks: {parallel_info['chunks_needed']}")
    print(f"  Expected Speedup: {parallel_info['estimated_speedup']}")
    
    # Define progress callback
    def progress_callback(info):
        print(f"  Chunk {info['chunk']}/{info['total_chunks']}: "
              f"{info['valid_so_far']:,} valid, {info['invalid_so_far']:,} invalid", 
              end='\r')
    
    # Validate with distributed processing
    print("\nValidating...")
    start = time.time()
    
    result = distributed_validator.validate_csv_parallel(test_file, callback=progress_callback)
    
    elapsed = time.time() - start
    throughput = result.total_rows / elapsed
    
    print(f"\n\n✓ Distributed validation completed!")
    print(f"  Total Rows: {result.total_rows:,}")
    print(f"  Valid: {result.valid_count:,}")
    print(f"  Invalid: {result.invalid_count:,}")
    print(f"  Time: {elapsed:.2f} seconds")
    print(f"  Throughput: {throughput:,.0f} rows/second")
    
    Path(test_file).unlink()


def example_cached_validation():
    """Example 3: Cached validation for repeated validations."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Cached Validation (Smart Re-use)")
    print("="*70)
    
    schema = Schema({
        'id': Field(str, required=True),
        'name': Field(str, required=True, min_length=2),
        'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
        'age': Field(str, required=True),
        'balance': Field(str, required=True),
    })
    
    # Generate test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_file = f.name
    
    generate_large_test_file(test_file, num_rows=100_000)
    
    # Create cached validator
    validator = Validator(schema=schema, parallel=True)
    cached_validator = CachedValidator(validator, cache_dir='/tmp/pyrustpipe_cache')
    
    # First validation (no cache)
    print("\nFirst validation (no cache)...")
    start = time.time()
    result1 = cached_validator.validate_csv(test_file, use_cache=True)
    elapsed1 = time.time() - start
    
    print(f"✓ First validation: {result1.total_rows:,} rows in {elapsed1:.2f}s")
    
    # Second validation (uses cache)
    print("\nSecond validation (with cache)...")
    start = time.time()
    result2 = cached_validator.validate_csv(test_file, use_cache=True)
    elapsed2 = time.time() - start
    
    print(f"✓ Second validation: {result2.total_rows:,} rows in {elapsed2:.2f}s")
    
    # Show speedup
    speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float('inf')
    print(f"\n📊 Cache Speedup: {speedup:.1f}x faster!")
    
    # Cache stats
    stats = cached_validator.get_cache_stats()
    print(f"\nCache Statistics:")
    print(f"  Entries: {stats['entries']}")
    print(f"  Size: {stats['cache_size_mb']:.2f} MB")
    print(f"  TTL: {stats['ttl_hours']} hours")
    
    Path(test_file).unlink()


def billion_record_strategy():
    """Example 4: Strategy for validating 1 billion+ records."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Billion-Record Processing Strategy")
    print("="*70)
    
    print("\nRecommended Architecture for 1B+ Records:")
    print("-" * 70)
    print("""
    1. STREAMING VALIDATOR (Memory Efficiency)
       - Buffer Size: 50,000-100,000 rows
       - Memory Usage: ~50-100 MB
       - Best for: Single-machine, large files
       - Throughput: 100k-500k rows/sec
    
    2. DISTRIBUTED VALIDATOR (Speed)
       - Workers: 8-32 (match CPU cores)
       - Chunk Size: 100,000-500,000 rows
       - Best for: Multi-core machines
       - Throughput: 1M-5M rows/sec (8-32x speedup)
    
    3. RUST SIMD OPTIMIZATIONS (Future)
       - Use AVX2/AVX-512 for pattern matching
       - Vectorized comparison operations
       - Expected: 10M+ rows/sec per core
    
    4. CACHING LAYER (Re-validation)
       - SHA256 file hashing
       - Avoid redundant validations
       - Speedup: 100-1000x for identical files
    
    5. MAPREDUCE FOR EXTREME SCALE
       - Spark/Ray integration
       - Distributed across cluster
       - Throughput: 100M+ rows/sec
    """)
    
    print("\nExample Timeline for 1 Billion Records:")
    print("-" * 70)
    
    scenarios = [
        ("Single-threaded Python", 1_000_000, 16, 667),
        ("Streaming Validator", 500_000, 16, 33),
        ("Distributed (8 cores)", 3_000_000, 16, 5.6),
        ("Distributed (32 cores)", 10_000_000, 16, 1.7),
        ("Future SIMD optimized", 50_000_000, 16, 0.3),
    ]
    
    for approach, throughput, file_size_gb, time_minutes in scenarios:
        print(f"  {approach:30s} | {throughput:>10,} rows/s | "
              f"{time_minutes:>5.1f} min for {file_size_gb}GB")
    
    print(f"\n💡 Current Implementation: Streaming + Distributed")
    print(f"   Expected Performance: 1-5M rows/second")
    print(f"   For 1B records: ~3-17 minutes on 8-core machine")


if __name__ == '__main__':
    print("="*70)
    print("PyRustPipe: Billion-Record Validation Examples")
    print("="*70)
    
    # Run examples
    try:
        example_streaming_validation()
        example_distributed_validation()
        example_cached_validation()
        billion_record_strategy()
        
        print("\n" + "="*70)
        print("✓ All examples completed successfully!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
