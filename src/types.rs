use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents a single validation rule
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationRule {
    pub name: String,
    pub field: String,
    pub rule_type: RuleType,
    pub params: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RuleType {
    Required,
    TypeCheck,
    Range,
    Pattern,
    Length,
    Custom,
}

/// Row data representation
#[derive(Debug, Clone)]
pub struct RowData {
    pub index: usize,
    pub data: HashMap<String, serde_json::Value>,
}

/// Validation error details
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct ValidationError {
    #[pyo3(get)]
    pub row_index: usize,
    #[pyo3(get)]
    pub field: String,
    #[pyo3(get)]
    pub rule: String,
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl ValidationError {
    fn __repr__(&self) -> String {
        format!(
            "ValidationError(row={}, field={}, rule={}, message={})",
            self.row_index, self.field, self.rule, self.message
        )
    }
}

/// Overall validation results
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[pyclass]
pub struct ValidationResult {
    #[pyo3(get)]
    pub valid_count: usize,
    #[pyo3(get)]
    pub invalid_count: usize,
    #[pyo3(get)]
    pub total_rows: usize,
    pub errors: Vec<ValidationError>,
}

#[pymethods]
impl ValidationResult {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    #[getter]
    fn errors(&self) -> Vec<ValidationError> {
        self.errors.clone()
    }

    fn success_rate(&self) -> f64 {
        if self.total_rows == 0 {
            0.0
        } else {
            (self.valid_count as f64 / self.total_rows as f64) * 100.0
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "ValidationResult(valid={}, invalid={}, total={}, success_rate={:.2}%)",
            self.valid_count,
            self.invalid_count,
            self.total_rows,
            self.success_rate()
        )
    }
}
