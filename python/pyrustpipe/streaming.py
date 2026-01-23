"""Streaming validator for processing files line-by-line without loading entire dataset into memory."""

import csv
from typing import Iterator, Optional, Generator, Tuple
from .types import ValidationResult, ValidationError
from .validator import Validator
from .schema import Schema


class StreamingValidator:
    """
    Memory-efficient validator for processing huge files line-by-line.
    
    Designed to handle files with billions of records without loading the
    entire dataset into memory. Perfect for:
    - Real-time data ingestion
    - Stream processing pipelines
    - Memory-constrained environments
    
    Example:
        >>> schema = Schema({'id': Field(int), 'name': Field(str)})
        >>> sv = StreamingValidator(schema=schema, buffer_size=10000)
        >>> for batch in sv.validate_csv_stream('huge_file.csv'):
        ...     print(f"Processed {batch.total_rows} rows")
    """
    
    def __init__(
        self,
        schema: Schema,
        buffer_size: int = 10000,
        parallel: bool = True,
        chunk_size: int = 5000,
    ):
        """
        Initialize StreamingValidator.
        
        Args:
            schema: Validation schema
            buffer_size: Number of rows to buffer before validation
            parallel: Use parallel processing for each buffer batch
            chunk_size: Chunk size for parallel processing
        """
        self.schema = schema
        self.buffer_size = buffer_size
        self.parallel = parallel
        self.chunk_size = chunk_size
        self.validator = Validator(schema=schema, parallel=parallel)
    
    def validate_csv_stream(
        self, filepath: str, skip_header: bool = True
    ) -> Generator[ValidationResult, None, None]:
        """
        Stream validation of CSV file, yielding results in batches.
        
        Memory usage: O(buffer_size) instead of O(file_size)
        
        Args:
            filepath: Path to CSV file
            skip_header: Skip first row (assume header)
            
        Yields:
            ValidationResult for each buffer batch
            
        Example:
            >>> for result in validator.validate_csv_stream('data.csv'):
            ...     print(f"Batch: {result.valid_count}/{result.total_rows}")
            ...     total_valid += result.valid_count
        """
        buffer = []
        row_count = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                if skip_header and row_count == 0:
                    row_count += 1
                    continue
                
                buffer.append(row)
                row_count += 1
                
                # Validate buffer when it reaches capacity
                if len(buffer) >= self.buffer_size:
                    result = self._validate_buffer(buffer, row_count)
                    buffer = []
                    yield result
        
        # Validate remaining rows
        if buffer:
            result = self._validate_buffer(buffer, row_count)
            yield result
    
    def _validate_buffer(self, buffer: list, row_count: int) -> ValidationResult:
        """Validate a buffer of rows."""
        total_valid = 0
        total_errors = []
        
        for row_idx, row_data in enumerate(buffer):
            errors = self.validator.validate_dict(row_data)
            if not errors:
                total_valid += 1
            else:
                for error in errors:
                    # Adjust row index to global position
                    error.row_index = row_count - len(buffer) + row_idx
                    total_errors.append(error)
        
        return ValidationResult(
            valid_count=total_valid,
            invalid_count=len(buffer) - total_valid,
            total_rows=len(buffer),
            errors=total_errors
        )
    
    def validate_json_stream(
        self, filepath: str
    ) -> Generator[ValidationResult, None, None]:
        """
        Stream validation of JSONL file (one JSON object per line).
        
        Args:
            filepath: Path to JSONL file
            
        Yields:
            ValidationResult for each buffer batch
        """
        import json
        
        buffer = []
        row_count = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    row_data = json.loads(line)
                    buffer.append(row_data)
                    row_count += 1
                    
                    if len(buffer) >= self.buffer_size:
                        result = self._validate_buffer(buffer, row_count)
                        buffer = []
                        yield result
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON at line {row_count}: {e}")
        
        if buffer:
            result = self._validate_buffer(buffer, row_count)
            yield result
    
    def estimate_memory_usage(self, file_size_gb: float) -> dict:
        """
        Estimate memory usage for processing a file.
        
        Args:
            file_size_gb: Size of file in gigabytes
            
        Returns:
            Dictionary with memory usage estimates
        """
        avg_row_size_bytes = 500  # Average row size estimate
        rows_per_gb = (1024 ** 3) / avg_row_size_bytes
        
        total_rows = file_size_gb * rows_per_gb
        buffer_memory_mb = (self.buffer_size * avg_row_size_bytes) / (1024 ** 2)
        
        return {
            'file_size_gb': file_size_gb,
            'estimated_rows': int(total_rows),
            'buffer_size_rows': self.buffer_size,
            'buffer_memory_mb': buffer_memory_mb,
            'batches_required': int(total_rows / self.buffer_size),
            'estimated_processing_time_sec': (total_rows / 1_000_000) * 5  # Rough estimate
        }


class LineProcessor:
    """
    Low-level line processor for maximum efficiency.
    
    Processes files line-by-line without buffering, useful for:
    - Microservices receiving streaming data
    - Real-time validation in data pipelines
    - Minimal memory footprint requirements
    """
    
    def __init__(self, schema: Schema):
        """Initialize LineProcessor."""
        self.schema = schema
        self.validator = Validator(schema=schema, parallel=False)
    
    def process_line(self, line_data: dict) -> Tuple[bool, Optional[list]]:
        """
        Process a single line of data.
        
        Args:
            line_data: Dictionary representation of a row
            
        Returns:
            Tuple of (is_valid, errors)
        """
        errors = self.validator.validate_dict(line_data)
        return len(errors) == 0, errors if errors else None


__all__ = ['StreamingValidator', 'LineProcessor']
