"""
Basic example: Validate user data
"""

from pyrustpipe import Validator, Schema, Field

# Define schema
user_schema = Schema({
    "name": Field(str, required=True, min_length=2, max_length=100),
    "email": Field(str, required=True, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$"),
    "age": Field(int, required=True, min=18, max=120),
    "balance": Field(float, min=0.0),
})

# Create validator
validator = Validator(schema=user_schema, parallel=True)

# Validate a single dictionary (Python-only, fast for testing)
test_data = {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 25,
    "balance": 1000.50
}

errors = validator.validate_dict(test_data)
if errors:
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✓ Data is valid!")

# Validate CSV file (uses Rust backend)
print("\nValidating CSV file...")
# result = validator.validate_csv("users.csv")
# print(result.summary())
