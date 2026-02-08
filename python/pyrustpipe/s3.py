"""S3 integration for pyrustpipe - streaming validation from AWS S3."""

import os
import io
import csv
import tempfile
from typing import Optional, Callable, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from .schema import Schema
from .validator import Validator
from .types import ValidationResult, ValidationError


class S3Validator:
    """
    Validate CSV files directly from AWS S3.
    
    Features:
    - Stream data from S3 without downloading entire file
    - Parallel chunk validation
    - Upload results back to S3
    - Progress callbacks
    
    Example:
        >>> from pyrustpipe import Schema, Field
        >>> from pyrustpipe.s3 import S3Validator
        >>> 
        >>> schema = Schema({
        ...     'id': Field(int, required=True),
        ...     'email': Field(str, pattern=r'^[\\w.-]+@[\\w.-]+\\.\\w+$'),
        ...     'amount': Field(float, min=0)
        ... })
        >>> 
        >>> validator = S3Validator(schema, workers=4)
        >>> result = validator.validate(
        ...     bucket='my-data-bucket',
        ...     key='transactions/2026-01-31.csv'
        ... )
        >>> print(f"Valid: {result.valid_count}, Invalid: {result.invalid_count}")
    
    Requires boto3: pip install boto3
    """
    
    def __init__(
        self,
        schema: Schema,
        workers: int = 4,
        chunk_size: int = 10000,
        region: Optional[str] = None,
    ):
        """
        Initialize S3Validator.
        
        Args:
            schema: Validation schema
            workers: Number of parallel workers for validation
            chunk_size: Rows per validation chunk
            region: AWS region (default: from environment or us-east-1)
        """
        self.schema = schema
        self.workers = workers
        self.chunk_size = chunk_size
        self.region = region or os.environ.get('AWS_REGION', 'us-east-1')
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of boto3 S3 client."""
        if self._client is None:
            try:
                import boto3
            except ImportError:
                raise ImportError(
                    "boto3 required for S3 support. Install with: pip install boto3"
                )
            self._client = boto3.client('s3', region_name=self.region)
        return self._client
    
    def validate(
        self,
        bucket: str,
        key: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ValidationResult:
        """
        Validate a CSV file from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (path to file)
            callback: Optional progress callback function
            
        Returns:
            ValidationResult with validation statistics
        """
        client = self._get_client()
        
        # Get object size for progress tracking
        head = client.head_object(Bucket=bucket, Key=key)
        total_size = head['ContentLength']
        
        # Download and stream-parse the file
        response = client.get_object(Bucket=bucket, Key=key)
        body = response['Body']
        
        # Read content and parse CSV
        content = body.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        # Collect rows into chunks
        chunks = []
        current_chunk = []
        
        for row in reader:
            current_chunk.append(row)
            if len(current_chunk) >= self.chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Validate chunks in parallel
        all_results = []
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = [
                executor.submit(self._validate_chunk, chunk, idx)
                for idx, chunk in enumerate(chunks)
            ]
            
            for i, future in enumerate(futures):
                result = future.result()
                all_results.append(result)
                
                if callback:
                    callback({
                        'chunk': i + 1,
                        'total_chunks': len(chunks),
                        'valid_so_far': sum(r.valid_count for r in all_results),
                        'invalid_so_far': sum(r.invalid_count for r in all_results),
                        'progress_pct': ((i + 1) / len(chunks)) * 100
                    })
        
        return self._aggregate_results(all_results)
    
    def validate_streaming(
        self,
        bucket: str,
        key: str,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ValidationResult:
        """
        Validate S3 file using streaming (memory-efficient for large files).
        
        Downloads file in chunks to minimize memory usage.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            callback: Optional progress callback
            
        Returns:
            ValidationResult
        """
        client = self._get_client()
        
        # Download to temp file and stream-validate
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
            
            # Streaming download
            response = client.get_object(Bucket=bucket, Key=key)
            for chunk in response['Body'].iter_chunks(chunk_size=8192):
                tmp.write(chunk)
        
        try:
            # Use streaming validator for memory efficiency
            from .streaming import StreamingValidator
            
            validator = StreamingValidator(
                schema=self.schema,
                chunk_size=self.chunk_size
            )
            
            result = validator.validate_file(tmp_path, callback=callback)
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
        
        return result
    
    def upload_results(
        self,
        result: ValidationResult,
        bucket: str,
        key: str,
    ) -> str:
        """
        Upload validation results to S3 as JSON.
        
        Args:
            result: ValidationResult to upload
            bucket: Destination S3 bucket
            key: Destination object key
            
        Returns:
            S3 URI of uploaded results
        """
        import json
        
        client = self._get_client()
        
        # Serialize results
        result_dict = {
            'valid_count': result.valid_count,
            'invalid_count': result.invalid_count,
            'total_rows': result.total_rows,
            'success_rate': result.success_rate(),
            'errors': [
                {'row_index': e.row_index, 'field': e.field, 'message': e.message}
                for e in (result.errors if hasattr(result, 'errors') and isinstance(result.errors, list) else [])
            ] if hasattr(result, 'errors') else []
        }
        
        json_data = json.dumps(result_dict, indent=2)
        
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
        
        return f"s3://{bucket}/{key}"
    
    def _validate_chunk(self, chunk: List[dict], chunk_idx: int) -> ValidationResult:
        """Validate a single chunk of rows."""
        validator = Validator(schema=self.schema, parallel=True)
        
        valid_count = 0
        errors = []
        
        for row_idx, row in enumerate(chunk):
            row_errors = validator.validate_dict(row)
            if not row_errors:
                valid_count += 1
            else:
                # Convert to error messages
                for err in row_errors:
                    errors.append(err)
        
        return ValidationResult(
            valid_count=valid_count,
            invalid_count=len(chunk) - valid_count,
            total_rows=len(chunk),
            errors=errors
        )
    
    def _aggregate_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Aggregate results from all chunks."""
        total_valid = sum(r.valid_count for r in results)
        total_invalid = sum(r.invalid_count for r in results)
        total_rows = sum(r.total_rows for r in results)
        
        all_errors = []
        for result in results:
            if hasattr(result, 'errors'):
                all_errors.extend(result.errors)
        
        return ValidationResult(
            valid_count=total_valid,
            invalid_count=total_invalid,
            total_rows=total_rows,
            errors=all_errors
        )


def validate_s3(
    bucket: str,
    key: str,
    schema: Schema,
    workers: int = 4,
    callback: Optional[Callable] = None,
) -> ValidationResult:
    """
    Convenience function to validate S3 file.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        schema: Validation schema
        workers: Number of parallel workers
        callback: Optional progress callback
        
    Returns:
        ValidationResult
    """
    validator = S3Validator(schema=schema, workers=workers)
    return validator.validate(bucket=bucket, key=key, callback=callback)


__all__ = ['S3Validator', 'validate_s3']
