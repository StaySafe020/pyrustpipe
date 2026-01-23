"""
Validation rules for user_validation
"""

from pyrustpipe import Schema, Field, validate


# Define schema
user_validation_schema = Schema({
    "id": Field(int, required=True, min=1),
    "name": Field(str, required=True, min_length=2, max_length=100),
    "email": Field(str, required=True, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "age": Field(int, min=0, max=150),
    "balance": Field(float, min=0.0),
})


# Custom validation rules (optional)
@validate
def check_age_consistency(row):
    """Ensure age is consistent with other fields"""
    if hasattr(row, "age") and hasattr(row, "birthdate"):
        # Add custom logic here
        pass
    return True


@validate(name="balance_check")
def check_balance_positive(row):
    """Ensure balance is non-negative"""
    assert row.balance >= 0, "Balance must be non-negative"


# Export the schema for CLI usage
schema = user_validation_schema
