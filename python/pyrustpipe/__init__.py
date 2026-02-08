"""
pyrustpipe - Fast data validation with Python DSL and Rust backend
"""

__version__ = "0.1.0"

from .validator import Validator
from .schema import Schema, Field
from .decorators import validate, rule
from .types import ValidationResult, ValidationError
from .streaming import StreamingValidator, LineProcessor
from .distributed import DistributedValidator, S3DistributedValidator, MapReduceValidator
from .caching import ValidationCache, CachedValidator
from .s3 import S3Validator, validate_s3

__all__ = [
    "Validator",
    "Schema",
    "Field",
    "validate",
    "rule",
    "ValidationResult",
    "ValidationError",
    "StreamingValidator",
    "LineProcessor",
    "DistributedValidator",
    "S3DistributedValidator",
    "MapReduceValidator",
    "ValidationCache",
    "CachedValidator",
    "S3Validator",
    "validate_s3",
]
