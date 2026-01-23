"""Tests for Validator class"""

import pytest
from pyrustpipe import Validator, Schema, Field, validate


def test_validator_creation():
    """Test basic validator creation"""
    schema = Schema({
        "name": Field(str, required=True),
        "age": Field(int, min=0)
    })
    
    validator = Validator(schema=schema)
    assert validator.schema is not None
    assert validator.parallel == True


def test_validator_validate_dict():
    """Test dictionary validation"""
    schema = Schema({
        "name": Field(str, required=True, min_length=2),
        "age": Field(int, min=18)
    })
    
    validator = Validator(schema=schema)
    
    # Valid data
    valid_data = {"name": "John", "age": 25}
    errors = validator.validate_dict(valid_data)
    assert len(errors) == 0
    
    # Invalid data
    invalid_data = {"name": "J", "age": 15}
    errors = validator.validate_dict(invalid_data)
    assert len(errors) > 0


def test_validator_with_custom_rules():
    """Test validator with custom rules"""
    @validate
    def check_even(row):
        assert row.value % 2 == 0, "Value must be even"
    
    validator = Validator(rules=[check_even])
    assert len(validator.rules) == 1


def test_rule_compilation():
    """Test rule compilation for Rust"""
    schema = Schema({
        "age": Field(int, required=True, min=18, max=120)
    })
    
    validator = Validator(schema=schema)
    rules = validator._compile_rules()
    
    assert isinstance(rules, list)
    assert len(rules) > 0
    assert all(isinstance(r, dict) for r in rules)
