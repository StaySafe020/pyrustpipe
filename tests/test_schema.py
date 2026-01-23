"""Tests for schema and field definitions"""

import pytest
from pyrustpipe.schema import Schema, Field


def test_field_creation():
    """Test basic field creation"""
    field = Field(str, required=True, min_length=2, max_length=100)
    assert field.field_type == str
    assert field.required == True
    assert field.min_length == 2
    assert field.max_length == 100


def test_field_to_rust_rules():
    """Test conversion to Rust rules"""
    field = Field(int, required=True, min=0, max=100)
    rules = field.to_rust_rules("age")
    
    assert len(rules) >= 2  # At least required and type check
    assert any(r["rule_type"] == "Required" for r in rules)
    assert any(r["rule_type"] == "TypeCheck" for r in rules)
    assert any(r["rule_type"] == "Range" for r in rules)


def test_schema_compilation():
    """Test schema compilation"""
    schema = Schema({
        "name": Field(str, required=True),
        "age": Field(int, min=0, max=120)
    })
    
    rules = schema.compile()
    assert len(rules) > 0
    assert isinstance(rules, list)


def test_schema_validate_dict_valid():
    """Test dictionary validation with valid data"""
    schema = Schema({
        "name": Field(str, required=True, min_length=2),
        "age": Field(int, min=18, max=120)
    })
    
    data = {"name": "John", "age": 25}
    errors = schema.validate_dict(data)
    assert len(errors) == 0


def test_schema_validate_dict_invalid():
    """Test dictionary validation with invalid data"""
    schema = Schema({
        "name": Field(str, required=True, min_length=2),
        "age": Field(int, min=18, max=120)
    })
    
    # Missing required field
    data1 = {"age": 25}
    errors1 = schema.validate_dict(data1)
    assert len(errors1) > 0
    assert any("required" in e.lower() for e in errors1)
    
    # Invalid type
    data2 = {"name": "John", "age": "twenty-five"}
    errors2 = schema.validate_dict(data2)
    assert len(errors2) > 0
    
    # Out of range
    data3 = {"name": "John", "age": 15}
    errors3 = schema.validate_dict(data3)
    assert len(errors3) > 0


def test_field_pattern_validation():
    """Test regex pattern validation"""
    schema = Schema({
        "email": Field(str, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    })
    
    # Valid email
    valid_data = {"email": "test@example.com"}
    errors = schema.validate_dict(valid_data)
    assert len(errors) == 0
    
    # Invalid email
    invalid_data = {"email": "not-an-email"}
    errors = schema.validate_dict(invalid_data)
    assert len(errors) > 0
