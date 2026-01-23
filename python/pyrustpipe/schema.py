"""Schema and Field definitions for validation rules"""

from typing import Any, Dict, List, Optional, Pattern, Union
from dataclasses import dataclass, field
import re


@dataclass
class Field:
    """Define validation rules for a single field"""
    
    field_type: type
    required: bool = False
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[Union[str, Pattern]] = None
    choices: Optional[List[Any]] = None
    custom_validator: Optional[callable] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Compile regex pattern if provided as string"""
        if isinstance(self.pattern, str):
            self.pattern = re.compile(self.pattern)
    
    def to_rust_rules(self, field_name: str) -> List[Dict[str, Any]]:
        """Convert field definition to Rust-compatible rule format"""
        rules = []
        
        # Required check
        if self.required:
            rules.append({
                "name": f"{field_name}_required",
                "field": field_name,
                "rule_type": "Required",
                "params": {}
            })
        
        # Type check
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean"
        }
        rules.append({
            "name": f"{field_name}_type",
            "field": field_name,
            "rule_type": "TypeCheck",
            "params": {"type": type_map.get(self.field_type, "string")}
        })
        
        # Range check
        if self.min is not None or self.max is not None:
            params = {}
            if self.min is not None:
                params["min"] = self.min
            if self.max is not None:
                params["max"] = self.max
            rules.append({
                "name": f"{field_name}_range",
                "field": field_name,
                "rule_type": "Range",
                "params": params
            })
        
        # Length check
        if self.min_length is not None or self.max_length is not None:
            params = {}
            if self.min_length is not None:
                params["min"] = self.min_length
            if self.max_length is not None:
                params["max"] = self.max_length
            rules.append({
                "name": f"{field_name}_length",
                "field": field_name,
                "rule_type": "Length",
                "params": params
            })
        
        # Pattern check
        if self.pattern is not None:
            rules.append({
                "name": f"{field_name}_pattern",
                "field": field_name,
                "rule_type": "Pattern",
                "params": {"pattern": self.pattern.pattern}
            })
        
        return rules


class Schema:
    """Define validation schema for structured data"""
    
    def __init__(self, fields: Dict[str, Field]):
        """
        Initialize schema with field definitions
        
        Args:
            fields: Dictionary mapping field names to Field objects
        """
        self.fields = fields
        self._compiled_rules = None
    
    def compile(self) -> List[Dict[str, Any]]:
        """Compile schema to Rust-compatible rule list"""
        if self._compiled_rules is not None:
            return self._compiled_rules
        
        all_rules = []
        for field_name, field_def in self.fields.items():
            all_rules.extend(field_def.to_rust_rules(field_name))
        
        self._compiled_rules = all_rules
        return all_rules
    
    def validate_dict(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate a dictionary against the schema (Python-side validation)
        
        Args:
            data: Dictionary to validate
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        for field_name, field_def in self.fields.items():
            value = data.get(field_name)
            
            # Required check
            if field_def.required and value is None:
                errors.append(f"Field '{field_name}' is required")
                continue
            
            if value is None:
                continue
            
            # Type check
            if not isinstance(value, field_def.field_type):
                errors.append(
                    f"Field '{field_name}' must be of type {field_def.field_type.__name__}"
                )
                continue
            
            # Range check for numbers
            if isinstance(value, (int, float)):
                if field_def.min is not None and value < field_def.min:
                    errors.append(f"Field '{field_name}' must be >= {field_def.min}")
                if field_def.max is not None and value > field_def.max:
                    errors.append(f"Field '{field_name}' must be <= {field_def.max}")
            
            # Length check for strings
            if isinstance(value, str):
                length = len(value)
                if field_def.min_length is not None and length < field_def.min_length:
                    errors.append(
                        f"Field '{field_name}' must have at least {field_def.min_length} characters"
                    )
                if field_def.max_length is not None and length > field_def.max_length:
                    errors.append(
                        f"Field '{field_name}' must have at most {field_def.max_length} characters"
                    )
            
            # Pattern check
            if field_def.pattern and isinstance(value, str):
                if not field_def.pattern.match(value):
                    errors.append(
                        f"Field '{field_name}' does not match required pattern"
                    )
            
            # Choices check
            if field_def.choices is not None and value not in field_def.choices:
                errors.append(
                    f"Field '{field_name}' must be one of {field_def.choices}"
                )
            
            # Custom validator
            if field_def.custom_validator is not None:
                try:
                    if not field_def.custom_validator(value):
                        msg = field_def.error_message or f"Field '{field_name}' failed custom validation"
                        errors.append(msg)
                except Exception as e:
                    errors.append(f"Field '{field_name}' validation error: {str(e)}")
        
        return errors
    
    def __repr__(self) -> str:
        return f"Schema(fields={list(self.fields.keys())})"
