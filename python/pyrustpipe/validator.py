"""Main validator class that orchestrates Python and Rust components"""

from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import json

from .schema import Schema, Field
from .decorators import ValidationRule, RuleSet
from .types import ValidationResult, ValidationError


class Validator:
    """
    Main validation orchestrator
    
    Handles Python DSL compilation and Rust engine invocation
    """
    
    def __init__(
        self,
        schema: Optional[Schema] = None,
        rules: Optional[List[ValidationRule]] = None,
        parallel: bool = True,
        chunk_size: int = 10000
    ):
        """
        Initialize validator
        
        Args:
            schema: Optional Schema object defining validation rules
            rules: Optional list of custom validation rules
            parallel: Whether to use parallel processing (default: True)
            chunk_size: Number of rows to process in each chunk (default: 10000)
        """
        self.schema = schema
        self.rules = rules or []
        self.parallel = parallel
        self.chunk_size = chunk_size
        self._rust_validator = None
    
    def _compile_rules(self) -> List[Dict[str, Any]]:
        """Compile Python rules to Rust-compatible format"""
        compiled_rules = []
        
        # Compile schema rules
        if self.schema:
            compiled_rules.extend(self.schema.compile())
        
        # Add custom rules (these will be Python callbacks)
        for rule in self.rules:
            compiled_rules.append({
                "name": rule.name,
                "field": "*",  # Applies to whole row
                "rule_type": "Custom",
                "params": {"callback": rule.func}
            })
        
        return compiled_rules
    
    def _get_rust_validator(self):
        """Lazy initialization of Rust validator"""
        if self._rust_validator is None:
            try:
                from pyrustpipe._core import RustValidator
                compiled_rules = self._compile_rules()
                self._rust_validator = RustValidator(compiled_rules, self.parallel)
            except ImportError as e:
                raise ImportError(
                    "Rust extension not found. Please build the extension with: "
                    "maturin develop --release"
                ) from e
        return self._rust_validator
    
    def validate_csv(
        self,
        path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None
    ) -> ValidationResult:
        """
        Validate a CSV file
        
        Args:
            path: Path to CSV file
            output_path: Optional path to save validation results
            
        Returns:
            ValidationResult object
        """
        path = str(path)
        validator = self._get_rust_validator()
        rust_result = validator.validate_csv(path, self.chunk_size)
        result = ValidationResult.from_rust(rust_result)
        
        if output_path:
            self._save_results(result, output_path)
        
        return result
    
    def validate_s3(
        self,
        bucket: str,
        key: str,
        output_bucket: Optional[str] = None,
        output_key: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate data from AWS S3
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            output_bucket: Optional bucket for results
            output_key: Optional key for results
            
        Returns:
            ValidationResult object
        """
        validator = self._get_rust_validator()
        rust_result = validator.validate_s3(bucket, key, self.chunk_size)
        result = ValidationResult.from_rust(rust_result)
        
        if output_bucket and output_key:
            # Upload results to S3
            from pyrustpipe._core import upload_results_to_s3
            import asyncio
            asyncio.run(upload_results_to_s3(output_bucket, output_key, rust_result))
        
        return result
    
    def validate_dict(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate a single dictionary using Rust engine
        
        Args:
            data: Dictionary to validate
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Use Rust engine for schema validation
        if self.schema:
            try:
                validator = self._get_rust_validator()
                rust_errors = validator.validate_dict(data)
                errors.extend(rust_errors)
            except Exception:
                # Fallback to Python validation if Rust fails
                errors.extend(self.schema.validate_dict(data))
        
        # Custom rule validation (Python callbacks)
        if self.rules:
            class DictRow:
                def __init__(self, d):
                    self.__dict__.update(d)
            
            row = DictRow(data)
            for rule in self.rules:
                try:
                    if not rule(row):
                        errors.append(f"Rule '{rule.name}' failed")
                except AssertionError as e:
                    errors.append(f"{rule.name}: {str(e)}")
                except Exception as e:
                    errors.append(f"{rule.name}: {str(e)}")
        
        return errors
    
    def _save_results(self, result: ValidationResult, path: Union[str, Path]):
        """Save validation results to file"""
        path = Path(path)
        
        # Convert to dict for JSON serialization
        result_dict = {
            "valid_count": result.valid_count,
            "invalid_count": result.invalid_count,
            "total_rows": result.total_rows,
            "success_rate": result.success_rate(),
            "errors": [
                {
                    "row_index": e.row_index,
                    "field": e.field,
                    "rule": e.rule,
                    "message": e.message
                }
                for e in result.errors
            ]
        }
        
        if path.suffix == ".json":
            with open(path, "w") as f:
                json.dump(result_dict, f, indent=2)
        else:
            # Default to JSON
            with open(path.with_suffix(".json"), "w") as f:
                json.dump(result_dict, f, indent=2)
    
    def __repr__(self) -> str:
        return (
            f"Validator(schema={self.schema is not None}, "
            f"rules={len(self.rules)}, parallel={self.parallel})"
        )
