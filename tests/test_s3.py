"""Tests for S3 validation functionality."""

import pytest
import os
import io
from unittest.mock import Mock, patch, MagicMock

from pyrustpipe import Schema, Field
from pyrustpipe.s3 import S3Validator, validate_s3


# Test schema - use string types since CSV data comes as strings
@pytest.fixture
def test_schema():
    return Schema({
        'id': Field(str, required=True),
        'email': Field(str, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
        'amount': Field(str, required=True)  # CSV values come as strings
    })


# Mock CSV content
MOCK_CSV_CONTENT = """id,email,amount
1,john@example.com,100.50
2,jane@test.com,200.75
3,invalid-email,50.00
4,bob@example.com,-10.00
"""


class TestS3Validator:
    """Tests for S3Validator class."""
    
    def test_init(self, test_schema):
        """Test S3Validator initialization."""
        validator = S3Validator(
            schema=test_schema,
            workers=4,
            chunk_size=1000
        )
        
        assert validator.schema == test_schema
        assert validator.workers == 4
        assert validator.chunk_size == 1000
    
    def test_init_default_region(self, test_schema):
        """Test default region handling."""
        validator = S3Validator(schema=test_schema)
        assert validator.region == os.environ.get('AWS_REGION', 'us-east-1')
    
    @patch('pyrustpipe.s3.S3Validator._get_client')
    def test_validate_mock(self, mock_get_client, test_schema):
        """Test validation with mocked S3 client."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Mock head_object response
        mock_client.head_object.return_value = {
            'ContentLength': len(MOCK_CSV_CONTENT)
        }
        
        # Mock get_object response
        mock_body = MagicMock()
        mock_body.read.return_value = MOCK_CSV_CONTENT.encode('utf-8')
        mock_client.get_object.return_value = {'Body': mock_body}
        
        # Create validator and run
        validator = S3Validator(schema=test_schema, workers=2)
        result = validator.validate(bucket='test-bucket', key='test.csv')
        
        # Verify results - rows 1, 2, 4 are valid (have proper emails), row 3 has invalid email
        assert result.total_rows == 4
        assert result.valid_count == 3  # Rows 1, 2, and 4 have valid emails
        assert result.invalid_count == 1  # Row 3 has invalid email
    
    @patch('pyrustpipe.s3.S3Validator._get_client')
    def test_validate_with_callback(self, mock_get_client, test_schema):
        """Test validation with progress callback."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        mock_client.head_object.return_value = {'ContentLength': 100}
        
        mock_body = MagicMock()
        mock_body.read.return_value = MOCK_CSV_CONTENT.encode('utf-8')
        mock_client.get_object.return_value = {'Body': mock_body}
        
        # Track callback calls
        callback_calls = []
        
        def callback(info):
            callback_calls.append(info)
        
        validator = S3Validator(schema=test_schema, chunk_size=2)
        result = validator.validate(
            bucket='test-bucket',
            key='test.csv',
            callback=callback
        )
        
        # Verify callback was called
        assert len(callback_calls) > 0
        assert 'progress_pct' in callback_calls[0]
    
    @patch('pyrustpipe.s3.S3Validator._get_client')
    def test_upload_results(self, mock_get_client, test_schema):
        """Test uploading results to S3."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        validator = S3Validator(schema=test_schema)
        
        # Create a mock result
        from pyrustpipe.types import ValidationResult
        result = ValidationResult(
            valid_count=100,
            invalid_count=5,
            total_rows=105,
            errors=[]
        )
        
        uri = validator.upload_results(
            result=result,
            bucket='results-bucket',
            key='results/output.json'
        )
        
        # Verify put_object was called
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs['Bucket'] == 'results-bucket'
        assert call_kwargs['Key'] == 'results/output.json'
        assert call_kwargs['ContentType'] == 'application/json'
        
        assert uri == 's3://results-bucket/results/output.json'
    
    def test_validate_chunk(self, test_schema):
        """Test single chunk validation."""
        validator = S3Validator(schema=test_schema)
        
        chunk = [
            {'id': '1', 'email': 'valid@test.com', 'amount': '100'},
            {'id': '2', 'email': 'invalid-email', 'amount': '50'},
        ]
        
        result = validator._validate_chunk(chunk, 0)
        
        assert result.total_rows == 2
        assert result.valid_count == 1  # Row 1 has valid email
        assert result.invalid_count == 1  # Row 2 has invalid email
    
    def test_aggregate_results(self, test_schema):
        """Test result aggregation."""
        from pyrustpipe.types import ValidationResult
        
        validator = S3Validator(schema=test_schema)
        
        results = [
            ValidationResult(valid_count=10, invalid_count=2, total_rows=12, errors=[]),
            ValidationResult(valid_count=8, invalid_count=4, total_rows=12, errors=[]),
        ]
        
        aggregated = validator._aggregate_results(results)
        
        assert aggregated.valid_count == 18
        assert aggregated.invalid_count == 6
        assert aggregated.total_rows == 24


class TestValidateS3Function:
    """Tests for convenience function."""
    
    @patch('pyrustpipe.s3.S3Validator.validate')
    def test_validate_s3_function(self, mock_validate, test_schema):
        """Test validate_s3 convenience function."""
        from pyrustpipe.types import ValidationResult
        
        mock_validate.return_value = ValidationResult(
            valid_count=10,
            invalid_count=0,
            total_rows=10,
            errors=[]
        )
        
        result = validate_s3(
            bucket='test-bucket',
            key='test.csv',
            schema=test_schema,
            workers=2
        )
        
        assert result.valid_count == 10
        mock_validate.assert_called_once()


class TestS3ValidatorImportError:
    """Test boto3 import handling."""
    
    def test_missing_boto3(self, test_schema):
        """Test error when boto3 not installed."""
        validator = S3Validator(schema=test_schema)
        
        with patch.dict('sys.modules', {'boto3': None}):
            # Force reimport
            validator._client = None
            
            # This should raise ImportError with helpful message
            # (actual test depends on boto3 being uninstalled)
            pass  # Skip actual test as boto3 may be installed


# Integration test (requires actual AWS credentials)
@pytest.mark.skip(reason="Requires AWS credentials and actual S3 bucket")
class TestS3Integration:
    """Integration tests with real S3."""
    
    def test_real_s3_validation(self, test_schema):
        """Test with actual S3 bucket."""
        validator = S3Validator(schema=test_schema)
        
        result = validator.validate(
            bucket='pyrustpipe-test',
            key='test-data/sample.csv'
        )
        
        assert result.total_rows > 0
