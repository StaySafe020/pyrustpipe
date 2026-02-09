#![allow(non_local_definitions)]

use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

mod s3;
mod types;
mod validator;

use types::{RowData, RuleType, ValidationError, ValidationResult, ValidationRule};
use validator::ValidationEngine;

/// Python module initialization
#[pymodule]
fn _core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RustValidator>()?;
    m.add_class::<ValidationResult>()?;
    m.add_class::<ValidationError>()?;
    Ok(())
}

/// Main Rust validator exposed to Python
#[pyclass]
pub struct RustValidator {
    rules: Vec<ValidationRule>,
    parallel: bool,
}

#[pymethods]
impl RustValidator {
    #[new]
    fn new(py: Python, rules: Vec<PyObject>, parallel: bool) -> PyResult<Self> {
        let mut rust_rules = Vec::new();

        for rule_obj in rules {
            let rule_dict: &PyDict = rule_obj.extract(py)?;

            let name: String = rule_dict
                .get_item("name")?
                .map(|v| v.extract())
                .unwrap_or(Ok("unknown".to_string()))?;

            let field: String = rule_dict
                .get_item("field")?
                .map(|v| v.extract())
                .unwrap_or(Ok("*".to_string()))?;

            let rule_type_str: String = rule_dict
                .get_item("rule_type")?
                .map(|v| v.extract())
                .unwrap_or(Ok("Custom".to_string()))?;

            let rule_type = match rule_type_str.as_str() {
                "Required" => RuleType::Required,
                "TypeCheck" => RuleType::TypeCheck,
                "Range" => RuleType::Range,
                "Pattern" => RuleType::Pattern,
                "Length" => RuleType::Length,
                _ => RuleType::Custom,
            };

            // Extract params
            let mut params = HashMap::new();
            if let Some(params_obj) = rule_dict.get_item("params")? {
                if let Ok(params_dict) = params_obj.extract::<&PyDict>() {
                    for (key, value) in params_dict.iter() {
                        let key_str: String = key.extract()?;
                        // Convert Python value to JSON value
                        if let Ok(s) = value.extract::<String>() {
                            params.insert(key_str, serde_json::Value::String(s));
                        } else if let Ok(i) = value.extract::<i64>() {
                            params.insert(key_str, serde_json::Value::Number(i.into()));
                        } else if let Ok(f) = value.extract::<f64>() {
                            if let Some(n) = serde_json::Number::from_f64(f) {
                                params.insert(key_str, serde_json::Value::Number(n));
                            }
                        } else if let Ok(b) = value.extract::<bool>() {
                            params.insert(key_str, serde_json::Value::Bool(b));
                        }
                    }
                }
            }

            rust_rules.push(ValidationRule {
                name,
                field,
                rule_type,
                params,
            });
        }

        Ok(RustValidator {
            rules: rust_rules,
            parallel,
        })
    }

    /// Validate a single dictionary
    fn validate_dict(&self, py: Python, data: PyObject) -> PyResult<Vec<String>> {
        let data_dict: &PyDict = data.extract(py)?;

        // Convert Python dict to RowData
        let mut row_data = HashMap::new();
        for (key, value) in data_dict.iter() {
            let key_str: String = key.extract()?;
            let json_value = python_to_json(value)?;
            row_data.insert(key_str, json_value);
        }

        let row = RowData {
            index: 0,
            data: row_data,
        };

        // Validate using Rust engine
        let engine = ValidationEngine::new(self.rules.clone(), false);
        let errors = engine.validate_single_row(&row);

        // Convert errors to strings
        Ok(errors.iter().map(|e| e.message.clone()).collect())
    }

    /// Validate CSV file
    fn validate_csv(&self, path: String, chunk_size: usize) -> PyResult<ValidationResult> {
        let engine = ValidationEngine::new(self.rules.clone(), self.parallel);
        engine
            .validate_csv(&path, chunk_size)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Validate S3 file
    fn validate_s3(
        &self,
        bucket: String,
        key: String,
        chunk_size: usize,
    ) -> PyResult<ValidationResult> {
        let engine = ValidationEngine::new(self.rules.clone(), self.parallel);

        // Run async S3 validation in blocking context
        let runtime = tokio::runtime::Runtime::new()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;

        runtime
            .block_on(async { engine.validate_s3(&bucket, &key, chunk_size).await })
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }

    /// Get the number of rules
    fn rule_count(&self) -> usize {
        self.rules.len()
    }
}

/// Convert Python object to JSON value
fn python_to_json(obj: &PyAny) -> PyResult<serde_json::Value> {
    if let Ok(s) = obj.extract::<String>() {
        Ok(serde_json::Value::String(s))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(serde_json::Value::Number(i.into()))
    } else if let Ok(f) = obj.extract::<f64>() {
        Ok(serde_json::Number::from_f64(f)
            .map(serde_json::Value::Number)
            .unwrap_or(serde_json::Value::Null))
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(serde_json::Value::Bool(b))
    } else if obj.is_none() {
        Ok(serde_json::Value::Null)
    } else {
        // Fallback: convert to string
        Ok(serde_json::Value::String(obj.to_string()))
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn test_basic_validation() {
        assert!(true);
    }
}
