import json
from typing import Dict, Any
from dataclasses import dataclass
from pyrustpipe import rust  # This will be the Rust module

class Schema:
    def __init__(self, schema_definition: Dict[str, Any]):
        self.definition = schema_definition
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data against the schema using Rust implementation"""
        return rust.validate_data(self.definition, data)

def validate(data: Dict[str, Any], schema: Schema) -> bool:
    """Convenience function for validation"""
    return schema.validate(data)