"""Python type definitions for validation results"""

from dataclasses import dataclass
from typing import List


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
    
    @classmethod
    def from_rust(cls, rust_result) -> "ValidationResult":
        """Convert Rust ValidationResult to Python ValidationResult"""
        errors = [
            ValidationError(
                row_index=e.row_index,
                field=e.field,
                rule=e.rule,
                message=e.message
            )
            for e in rust_result.errors
        ]
        return cls(
            valid_count=rust_result.valid_count,
            invalid_count=rust_result.invalid_count,
            total_rows=rust_result.total_rows,
            errors=errors
        )
