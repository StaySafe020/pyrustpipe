"""
Example: Using custom validation rules with decorators
"""

from pyrustpipe import Validator, validate, rule

# Define custom rules using decorators
@validate
def check_age_adult(row):
    """Ensure user is an adult"""
    assert row.age >= 18, "Must be 18 or older"

@validate(name="email_check")
def check_valid_email(row):
    """Basic email validation"""
    assert "@" in row.email and "." in row.email, "Invalid email format"

@validate
def check_balance_reasonable(row):
    """Ensure balance is within reasonable limits"""
    assert 0 <= row.balance <= 1000000, "Balance must be between 0 and 1M"

# Create validator with custom rules
validator = Validator(rules=[check_age_adult, check_valid_email, check_balance_reasonable])

# Test with sample data
class User:
    def __init__(self, name, email, age, balance):
        self.name = name
        self.email = email
        self.age = age
        self.balance = balance

# Valid user
valid_user = User("Alice", "alice@example.com", 25, 5000.0)
print("Testing valid user...")
# result = validator.validate([valid_user])

# Invalid user
invalid_user = User("Bob", "invalid-email", 16, -100.0)
print("Testing invalid user...")
# result = validator.validate([invalid_user])
