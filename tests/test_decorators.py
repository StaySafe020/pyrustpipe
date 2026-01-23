"""Tests for validation decorators"""

import pytest
from pyrustpipe.decorators import validate, rule, ValidationRule


def test_validate_decorator():
    """Test basic validate decorator"""
    @validate
    def check_positive(row):
        assert row.value > 0, "Value must be positive"
    
    assert isinstance(check_positive, ValidationRule)
    assert check_positive.name == "check_positive"


def test_validate_decorator_with_name():
    """Test validate decorator with custom name"""
    @validate(name="custom_check")
    def check_something(row):
        return True
    
    assert isinstance(check_something, ValidationRule)
    assert check_something.name == "custom_check"


def test_validation_rule_execution():
    """Test validation rule execution"""
    @validate
    def check_age(row):
        assert row.age >= 18, "Must be adult"
    
    class ValidRow:
        age = 25
    
    class InvalidRow:
        age = 15
    
    assert check_age(ValidRow()) == True
    assert check_age(InvalidRow()) == False


def test_rule_function():
    """Test rule() function for simple rules"""
    age_rule = rule("age", min=18, max=120)
    
    assert isinstance(age_rule, ValidationRule)
    
    class ValidRow:
        age = 25
    
    class InvalidRow:
        age = 15
    
    assert age_rule(ValidRow()) == True
    assert age_rule(InvalidRow()) == False


def test_rule_pattern():
    """Test rule with pattern matching"""
    email_rule = rule("email", pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    
    class ValidRow:
        email = "test@example.com"
    
    class InvalidRow:
        email = "not-an-email"
    
    assert email_rule(ValidRow()) == True
    assert email_rule(InvalidRow()) == False
