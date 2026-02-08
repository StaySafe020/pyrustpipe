"""Distributed validator for processing files in parallel chunks across multiple workers."""

import os
import asyncio
from typing import List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from .types import ValidationResult, ValidationError
from .validator import Validator
from .schema import Schema


class DistributedValidator:
    """
    Distributed validation for massive datasets.
    
    Splits large files into chunks and validates them in parallel using:
    - ThreadPoolExecutor for I/O-bound operations
    - ProcessPoolExecutor for CPU-bound validation
    
    Perfect for:
    - 1B+ row processing on multi-core machines
    - S3 multi-part download and validation
    - MapReduce-style batch processing
    
    Example:
        >>> schema = Schema({'id': Field(int), 'amount': Field(float)})
        >>> dv = DistributedValidator(schema=schema, workers=8)
        >>> result = dv.validate_csv_parallel('huge_file.csv')
        >>> print(f"Validated {result.total_rows} rows across {dv.workers} workers")
    """
    
    def __init__(
        self,
        schema: Schema,
        workers: Optional[int] = None,
        chunk_size: int = 50000,
        use_processes: bool = False,
    ):
        """
        Initialize DistributedValidator.
        
        Args:
            schema: Validation schema
            workers: Number of parallel workers (default: CPU count)
            chunk_size: Rows per chunk
            use_processes: Use ProcessPoolExecutor instead of ThreadPoolExecutor
        """
        self.schema = schema
        self.workers = workers or os.cpu_count() or 4
        self.chunk_size = chunk_size
        self.use_processes = use_processes
    
    def validate_csv_parallel(
        self, filepath: str, callback: Optional[Callable] = None
    ) -> ValidationResult:
        """
        Validate CSV file in parallel chunks.
        
        Args:
            filepath: Path to CSV file
            callback: Optional progress callback function
            
        Returns:
            Aggregated ValidationResult from all chunks
        """
        import csv
        
        # Read file in chunks
        chunks = self._read_csv_chunks(filepath)
        
        # Validate chunks in parallel
        if self.use_processes:
            executor_class = ProcessPoolExecutor
        else:
            executor_class = ThreadPoolExecutor
        
        all_results = []
        with executor_class(max_workers=self.workers) as executor:
            futures = []
            chunk_num = 0
            
            for chunk in chunks:
                future = executor.submit(self._validate_chunk, chunk, chunk_num)
                futures.append(future)
                chunk_num += 1
            
            for i, future in enumerate(futures):
                result = future.result()
                all_results.append(result)
                
                if callback:
                    callback({
                        'chunk': i + 1,
                        'total_chunks': len(futures),
                        'valid_so_far': sum(r.valid_count for r in all_results),
                        'invalid_so_far': sum(r.invalid_count for r in all_results),
                    })
        
        return self._aggregate_results(all_results)
    
    def _read_csv_chunks(self, filepath: str) -> List[List[dict]]:
        """Read CSV file and split into chunks."""
        import csv
        
        chunks = []
        current_chunk = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                current_chunk.append(row)
                
                if len(current_chunk) >= self.chunk_size:
                    chunks.append(current_chunk)
                    current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _validate_chunk(
        self, chunk: List[dict], chunk_num: int
    ) -> ValidationResult:
        """Validate a single chunk of rows."""
        validator = Validator(schema=self.schema, parallel=True)
        
        total_valid = 0
        total_errors = []
        
        for row_idx, row_data in enumerate(chunk):
            errors = validator.validate_dict(row_data)
            if not errors:
                total_valid += 1
            else:
                total_errors.extend(errors)
        
        return ValidationResult(
            valid_count=total_valid,
            invalid_count=len(chunk) - total_valid,
            total_rows=len(chunk),
            errors=total_errors
        )
    
    def _aggregate_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Aggregate results from all chunks."""
        total_valid = sum(r.valid_count for r in results)
        total_invalid = sum(r.invalid_count for r in results)
        total_rows = sum(r.total_rows for r in results)
        all_errors = []
        
        for result in results:
            all_errors.extend(result.errors)
        
        return ValidationResult(
            valid_count=total_valid,
            invalid_count=total_invalid,
            total_rows=total_rows,
            errors=all_errors
        )
    
    def get_parallelization_info(self, file_size_gb: float) -> dict:
        """
        Get information about how the file will be parallelized.
        
        Args:
            file_size_gb: Size of file in gigabytes
            
        Returns:
            Dictionary with parallelization details
        """
        avg_row_size = 500
        rows_per_gb = (1024 ** 3) / avg_row_size
        total_rows = file_size_gb * rows_per_gb
        num_chunks = max(1, int(total_rows / self.chunk_size))
        
        # Limit chunks to number of workers (no point in more chunks than workers)
        effective_chunks = min(num_chunks, self.workers)
        
        return {
            'file_size_gb': file_size_gb,
            'estimated_rows': int(total_rows),
            'chunk_size': self.chunk_size,
            'chunks_needed': num_chunks,
            'worker_threads': self.workers,
            'effective_parallelism': effective_chunks,
            'estimated_speedup': f"{effective_chunks}x vs single-threaded",
            'processing_per_chunk_sec': (self.chunk_size / 1_000_000) * 5,
            'estimated_total_time_sec': (total_rows / (self.workers * 200_000))  # Rough estimate
        }


class S3DistributedValidator:
    """
    Distributed validator for files stored in AWS S3.
    
    Features:
    - Multi-part download optimization
    - Parallel chunk validation
    - Error aggregation with S3 object metadata
    
    Requires AWS credentials configured.
    """
    
    def __init__(
        self,
        schema: Schema,
        workers: Optional[int] = None,
        chunk_size: int = 50000,
        part_size: int = 10 * 1024 * 1024,  # 10MB per part
    ):
        """
        Initialize S3DistributedValidator.
        
        Args:
            schema: Validation schema
            workers: Number of parallel workers
            chunk_size: Validation chunk size (rows)
            part_size: S3 download part size (bytes)
        """
        self.schema = schema
        self.workers = workers or 4
        self.chunk_size = chunk_size
        self.part_size = part_size
    
    async def validate_s3_parallel(
        self, bucket: str, key: str, callback: Optional[Callable] = None
    ) -> ValidationResult:
        """
        Validate CSV file in S3 in parallel.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            callback: Optional progress callback
            
        Returns:
            Aggregated ValidationResult
        """
        # Use the S3Validator for actual implementation
        from .s3 import S3Validator
        
        s3_validator = S3Validator(
            schema=self.schema,
            workers=self.workers,
            chunk_size=self.chunk_size
        )
        
        return s3_validator.validate(bucket=bucket, key=key, callback=callback)


class MapReduceValidator:
    """
    MapReduce-style validator for extreme scalability.
    
    Implements map-reduce pattern:
    - MAP: Validate chunks in parallel
    - REDUCE: Aggregate results
    
    Perfect for frameworks like Apache Spark or Ray.
    """
    
    def __init__(self, schema: Schema):
        """Initialize MapReduceValidator."""
        self.schema = schema
    
    def map_validate_chunk(self, chunk_data: List[dict]) -> dict:
        """
        Map phase: Validate a chunk of rows.
        
        Args:
            chunk_data: List of row dictionaries
            
        Returns:
            Dictionary with validation statistics
        """
        validator = Validator(schema=self.schema, parallel=True)
        
        valid = 0
        errors = []
        
        for row in chunk_data:
            row_errors = validator.validate_dict(row)
            if not row_errors:
                valid += 1
            else:
                errors.extend(row_errors)
        
        return {
            'valid': valid,
            'invalid': len(chunk_data) - valid,
            'total': len(chunk_data),
            'errors': errors
        }
    
    def reduce_results(self, map_results: List[dict]) -> ValidationResult:
        """
        Reduce phase: Aggregate all map results.
        
        Args:
            map_results: List of results from map phase
            
        Returns:
            Final aggregated ValidationResult
        """
        total_valid = sum(r['valid'] for r in map_results)
        total_invalid = sum(r['invalid'] for r in map_results)
        total_rows = sum(r['total'] for r in map_results)
        
        all_errors = []
        for result in map_results:
            all_errors.extend(result.get('errors', []))
        
        return ValidationResult(
            valid_count=total_valid,
            invalid_count=total_invalid,
            total_rows=total_rows,
            errors=all_errors
        )


__all__ = ['DistributedValidator', 'S3DistributedValidator', 'MapReduceValidator']
