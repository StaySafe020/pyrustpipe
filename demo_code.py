from pyrustpipe import Validator, Schema, Field

# Define validation rules in simple Python
schema = Schema({
    'id': Field(str, required=True),
    'email': Field(str, required=True, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$'),
    'age': Field(int, required=True, min=18, max=120),
    'balance': Field(float, required=True, min=0.0)
})

# Validate the data directly with dicts
test_data = [
    {'id': '1', 'email': 'john@example.com', 'age': 25, 'balance': 1000.50},
    {'id': '2', 'email': 'jane@example.com', 'age': 30, 'balance': 2500.75},
    {'id': '3', 'email': 'invalid-email', 'age': 15, 'balance': 500.00},
    {'id': '4', 'email': 'bob@test.com', 'age': 150, 'balance': 9999.99},
]

validator = Validator(schema=schema, parallel=True)

print(f"\n✓ Validating 4 records...\n")

valid_count = 0
for idx, record in enumerate(test_data, 1):
    errors = validator.validate_dict(record)
    if not errors:
        valid_count += 1
        print(f"  Row {idx}: ✓ VALID")
    else:
        print(f"  Row {idx}: ❌ INVALID ({len(errors)} error(s))")

print(f"\n✓ Results: {valid_count} valid, {len(test_data)-valid_count} invalid")
print(f"  Success Rate: {(valid_count/len(test_data))*100:.0f}%")
