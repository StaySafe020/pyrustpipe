"""Decorator-based validation rule definitions"""

from functools import wraps
from typing import Any, Callable, Dict, List
import inspect


class ValidationRule:
    """Wrapper for validation rule functions"""
    
    def __init__(self, func: Callable, name: str = None):
        self.func = func
        self.name = name or func.__name__
        self.signature = inspect.signature(func)
        wraps(func)(self)
    
    def __call__(self, row: Any) -> bool:
        """Execute the validation rule"""
        try:
            result = self.func(row)
            # If function returns bool, use it; otherwise assume True if no exception
            return result if isinstance(result, bool) else True
        except AssertionError as e:
            # Assertion failed - validation failed
            return False
        except Exception as e:
            # Other exceptions also indicate failure
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        return {
            "name": self.name,
            "function": self.func,
            "type": "custom"
        }


def validate(func: Callable = None, *, name: str = None):
    """
    Decorator to mark a function as a validation rule
    
    Usage:
        @validate
        def check_age(row):
            assert row.age >= 18, "Must be 18 or older"
        
        @validate(name="email_check")
        def check_email(row):
            assert "@" in row.email, "Invalid email"
    """
    def decorator(f):
        return ValidationRule(f, name=name)
    
    if func is None:
        # Called with arguments: @validate(name="...")
        return decorator
    else:
        # Called without arguments: @validate
        return decorator(func)


def rule(field: str, **conditions):
    """
    Create a simple validation rule from conditions
    
    Usage:
        age_rule = rule("age", min=18, max=120)
        email_rule = rule("email", pattern=r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$")
    """
    def validator(row):
        value = getattr(row, field, None)
        
        if value is None:
            if conditions.get("required", False):
                raise AssertionError(f"Field '{field}' is required")
            return True
        
        # Check min/max for numbers
        if "min" in conditions and value < conditions["min"]:
            raise AssertionError(f"{field} must be >= {conditions['min']}")
        if "max" in conditions and value > conditions["max"]:
            raise AssertionError(f"{field} must be <= {conditions['max']}")
        
        # Check length for strings
        if "min_length" in conditions and len(value) < conditions["min_length"]:
            raise AssertionError(f"{field} must have at least {conditions['min_length']} characters")
        if "max_length" in conditions and len(value) > conditions["max_length"]:
            raise AssertionError(f"{field} must have at most {conditions['max_length']} characters")
        
        # Check pattern
        if "pattern" in conditions:
            import re
            pattern = re.compile(conditions["pattern"])
            if not pattern.match(str(value)):
                raise AssertionError(f"{field} does not match required pattern")
        
        return True
    
    return ValidationRule(validator, name=f"{field}_rule")


class RuleSet:
    """Collection of validation rules"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
    
    def add(self, rule: ValidationRule):
        """Add a rule to the set"""
        self.rules.append(rule)
        return self
    
    def validate_row(self, row: Any) -> List[str]:
        """Validate a row against all rules"""
        errors = []
        for rule in self.rules:
            try:
                if not rule(row):
                    errors.append(f"Rule '{rule.name}' failed")
            except AssertionError as e:
                errors.append(f"{rule.name}: {str(e)}")
            except Exception as e:
                errors.append(f"{rule.name}: Unexpected error - {str(e)}")
        return errors
    
    def __iter__(self):
        return iter(self.rules)
    
    def __len__(self):
        return len(self.rules)
