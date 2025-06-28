from dataclasses import dataclass
from typing import Callable, Dict, Type
import json

@dataclass
class Field:
    type: Type
    required: bool = False

class Pipeline:
    def __init__(self):
        self.fields: Dict[str, Field] = {}

    def field(self, type: Type, required: bool = False) -> Callable:
        def decorator(func: Callable) -> Callable:
            field_name = func.__name__
            self.fields[field_name] = Field(type=type, required=required)
            return func
        return decorator

    def to_schema(self) -> str:
        schema = {
            "fields": {
                name: {
                    "type": field.type.__name__,
                    "required": field.required
                }
                for name, field in self.fields.items()
            }
        }
        return json.dumps(schema)

def Pipeline(cls):
    pipeline = Pipeline()
    setattr(cls, '_pipeline', pipeline)
    original_init = cls.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._pipeline = pipeline

    cls.__init__ = new_init
    return cls