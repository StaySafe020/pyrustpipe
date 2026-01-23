"""Python type definitions and wrappers for Rust types"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationError:
    """Represents a single validation error"""
    row_index: int
    field: str
    rule: str
    message: str
    
    def __repr__(self) -> str:
        return (
            f"ValidationError(row={self.row_index}, field={self.field}, "
            f"rule={self.rule}, message='{self.message}')"
        )


@dataclass
class ValidationResult:
    """Results from a validation run"""
    valid_count: int = 0
    invalid_count: int = 0
    total_rows: int = 0
    errors: List[ValidationError] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def success_rate(self) -> float:
        """Calculate validation success rate as percentage"""
        if self.total_rows == 0:
            return 0.0
        return (self.valid_count / self.total_rows) * 100.0
    
    def is_valid(self) -> bool:
        """Check if all rows passed validation"""
        return self.invalid_count == 0
    
    def get_errors_by_field(self, field: str) -> List[ValidationError]:
        """Get all errors for a specific field"""
        return [e for e in self.errors if e.field == field]
    
    def get_errors_by_rule(self, rule: str) -> List[ValidationError]:
        """Get all errors for a specific rule"""
        return [e for e in self.errors if e.rule == rule]
    
    def summary(self) -> str:
        """Get a human-readable summary"""
        return (
            f"Validation Summary:\n"
            f"  Total Rows: {self.total_rows}\n"
            f"  Valid: {self.valid_count}\n"
            f"  Invalid: {self.invalid_count}\n"
            f"  Success Rate: {self.success_rate():.2f}%\n"
            f"  Total Errors: {len(self.errors)}"
        )
    
    def __repr__(self) -> str:
        return (
            f"ValidationResult(valid={self.valid_count}, invalid={self.invalid_count}, "
            f"total={self.total_rows}, success_rate={self.success_rate():.2f}%)"
        )


# Try to import Rust types, fall back to Python versions
try:
    from pyrustpipe._core import ValidationResult as RustValidationResult
    from pyrustpipe._core import ValidationError as RustValidationError
    
    # Wrap Rust types for additional Python functionality
    class ValidationResultWrapper(RustValidationResult):
        """Wrapper that adds Python methods to Rust ValidationResult"""
        
        def is_valid(self) -> bool:
            return self.invalid_count == 0
        
        def get_errors_by_field(self, field: str) -> List:
            return [e for e in self.errors if e.field == field]
        
        def get_errors_by_rule(self, rule: str) -> List:
            return [e for e in self.errors if e.rule == rule]
        
        def summary(self) -> str:
            return (
                f"Validation Summary:\n"
                f"  Total Rows: {self.total_rows}\n"
                f"  Valid: {self.valid_count}\n"
                f"  Invalid: {self.invalid_count}\n"
                f"  Success Rate: {self.success_rate():.2f}%\n"
                f"  Total Errors: {len(self.errors())}"
            )
    
    # Use Rust types when available
    ValidationResult = ValidationResultWrapper
    ValidationError = RustValidationError
    
except ImportError:
    # Fall back to pure Python types defined above
    pass
