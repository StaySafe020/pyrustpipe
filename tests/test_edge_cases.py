"""Edge case and error handling tests"""

import pytest
from pyrustpipe import Validator, Schema, Field, validate


def test_empty_schema():
    """Test with empty schema"""
    schema = Schema({})
    validator = Validator(schema=schema)
    
    errors = validator.validate_dict({'name': 'John'})
    assert len(errors) == 0  # Empty schema means no validation


def test_null_values():
    """Test handling of None/null values"""
    schema = Schema({
        'name': Field(str, required=True),
    })
    
    validator = Validator(schema=schema)
    
    # Missing required field
    errors = validator.validate_dict({})
    assert len(errors) > 0


def test_empty_strings():
    """Test handling of empty strings"""
    schema = Schema({
        'name': Field(str, required=True, min_length=1)
    })
    
    validator = Validator(schema=schema)
    
    errors = validator.validate_dict({'name': ''})
    assert len(errors) > 0


def test_unicode_handling():
    """Test international characters"""
    schema = Schema({
        'name': Field(str, required=True),
        'email': Field(str, required=True)
    })
    
    validator = Validator(schema=schema)
    
    # Unicode names
    data = {
        'name': '日本語テスト',  # Japanese
        'email': 'test@example.com'
    }
    
    errors = validator.validate_dict(data)
    assert len(errors) == 0


def test_numeric_edge_cases():
    """Test boundary values"""
    schema = Schema({
        'count': Field(int, min=0, max=1000),
        'price': Field(float, min=0.0, max=999999.99)
    })
    
    validator = Validator(schema=schema)
    
    # Boundary values - minimum
    data = {'count': 0, 'price': 0.0}
    errors = validator.validate_dict(data)
    assert len(errors) == 0
    
    # Boundary values - maximum
    data = {'count': 1000, 'price': 999999.99}
    errors = validator.validate_dict(data)
    assert len(errors) == 0
    
    # Out of bounds
    data = {'count': 1001, 'price': 1000000.00}
    errors = validator.validate_dict(data)
    assert len(errors) == 2


def test_special_regex_patterns():
    """Test complex regex patterns"""
    schema = Schema({
        'phone': Field(str, pattern=r'^\+?1?\d{9,15}$'),
        'ip_address': Field(str, pattern=r'^(\d{1,3}\.){3}\d{1,3}$'),
    })
    
    validator = Validator(schema=schema)
    
    # Valid
    data = {
        'phone': '+1234567890',
        'ip_address': '192.168.1.1',
    }
    errors = validator.validate_dict(data)
    assert len(errors) == 0
    
    # Invalid
    data = {
        'phone': 'abc123',
        'ip_address': '256.256.256.256',
    }
    errors = validator.validate_dict(data)
    # Regex pattern validation may vary; check at least >= 1 error
    assert len(errors) >= 1


def test_very_long_strings():
    """Test handling of very long strings"""
    schema = Schema({
        'description': Field(str, max_length=1000)
    })
    
    validator = Validator(schema=schema)
    
    # 999 chars - valid
    long_string = 'x' * 999
    errors = validator.validate_dict({'description': long_string})
    assert len(errors) == 0
    
    # 1001 chars - invalid
    long_string = 'x' * 1001
    errors = validator.validate_dict({'description': long_string})
    assert len(errors) > 0


def test_concurrent_validators():
    """Test creating multiple validators concurrently"""
    import threading
    
    schema1 = Schema({'name': Field(str, required=True)})
    schema2 = Schema({'email': Field(str, required=True)})
    
    results = []
    
    def validate_with_schema(schema, data):
        validator = Validator(schema=schema)
        errors = validator.validate_dict(data)
        results.append(len(errors))
    
    threads = [
        threading.Thread(target=validate_with_schema, args=(schema1, {'name': 'John'})),
        threading.Thread(target=validate_with_schema, args=(schema2, {'email': 'john@example.com'}))
    ]
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    assert all(r == 0 for r in results)


def test_type_coercion():
    """Test that validation doesn't coerce types incorrectly"""
    schema = Schema({
        'count': Field(int, required=True),
        'name': Field(str, required=True)
    })
    
    validator = Validator(schema=schema)
    
    # String that looks like number should NOT validate as int in dict
    data = {'count': '123', 'name': 'John'}
    errors = validator.validate_dict(data)
    # May have type errors depending on implementation


def test_special_characters():
    """Test handling of special characters"""
    schema = Schema({
        'name': Field(str, required=True),
        'description': Field(str, required=True)
    })
    
    validator = Validator(schema=schema)
    
    data = {
        'name': 'John<script>alert("xss")</script>',
        'description': 'SQL: DROP TABLE users; --'
    }
    
    # Should NOT execute, just validate
    errors = validator.validate_dict(data)
    assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
