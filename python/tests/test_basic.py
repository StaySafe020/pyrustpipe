import pytest
import pyrustpipe

def test_validate():
    schema = '{"fields": {"id": {"type": "int", "required": true}}}'
    data = '[{"id": 1}, {"id": "invalid"}]'
    errors = pyrustpipe.validate(schema, data)
    assert len(errors) == 2
    assert len(errors[0]) == 0  # First record is valid
    assert len(errors[1]) == 1  # Second record has a type error
    assert str(errors[1][0]) == "id: Expected type int"