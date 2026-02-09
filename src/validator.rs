use crate::types::{RowData, ValidationError, ValidationResult, ValidationRule};
use anyhow::{Context, Result};
use csv::ReaderBuilder;
use rayon::prelude::*;
use std::collections::HashMap;
use std::fs::File;

pub struct ValidationEngine {
    rules: Vec<ValidationRule>,
    parallel: bool,
}

impl ValidationEngine {
    pub fn new(rules: Vec<ValidationRule>, parallel: bool) -> Self {
        Self { rules, parallel }
    }

    /// Validate CSV file with chunked processing
    pub fn validate_csv(&self, path: &str, chunk_size: usize) -> Result<ValidationResult> {
        let file = File::open(path).context("Failed to open CSV file")?;
        let mut reader = ReaderBuilder::new().has_headers(true).from_reader(file);

        let headers: Vec<String> = reader
            .headers()
            .context("Failed to read CSV headers")?
            .iter()
            .map(|s| s.to_string())
            .collect();

        let mut result = ValidationResult::default();
        let mut rows: Vec<RowData> = Vec::new();

        // Read and validate in chunks
        for (row_index, record) in reader.records().enumerate() {
            let record = record.context("Failed to read CSV record")?;

            let mut row_data = HashMap::new();
            for (i, field) in record.iter().enumerate() {
                if i < headers.len() {
                    row_data.insert(
                        headers[i].clone(),
                        serde_json::Value::String(field.to_string()),
                    );
                }
            }

            rows.push(RowData {
                index: row_index,
                data: row_data,
            });

            // Process chunk when full
            if rows.len() >= chunk_size {
                let chunk_result = self.validate_chunk(&rows);
                result.merge(chunk_result);
                rows.clear();
            }
        }

        // Process remaining rows
        if !rows.is_empty() {
            let chunk_result = self.validate_chunk(&rows);
            result.merge(chunk_result);
        }

        Ok(result)
    }

    /// Validate a chunk of rows
    fn validate_chunk(&self, rows: &[RowData]) -> ValidationResult {
        let errors: Vec<Vec<ValidationError>> = if self.parallel {
            rows.par_iter().map(|row| self.validate_row(row)).collect()
        } else {
            rows.iter().map(|row| self.validate_row(row)).collect()
        };

        let mut total_valid = 0;
        let mut total_invalid = 0;
        let mut all_errors = Vec::new();

        for row_errors in errors {
            if row_errors.is_empty() {
                total_valid += 1;
            } else {
                total_invalid += 1;
                all_errors.extend(row_errors);
            }
        }

        ValidationResult {
            valid_count: total_valid,
            invalid_count: total_invalid,
            total_rows: rows.len(),
            errors: all_errors,
        }
    }

    /// Validate a single row and return errors (public interface for Python)
    pub fn validate_single_row(&self, row: &RowData) -> Vec<ValidationError> {
        self.validate_row(row)
    }

    /// Validate a single row against all rules
    fn validate_row(&self, row: &RowData) -> Vec<ValidationError> {
        let mut errors = Vec::new();

        for rule in &self.rules {
            if let Some(error) = self.apply_rule(rule, row) {
                errors.push(error);
            }
        }

        errors
    }

    /// Apply a single rule to a row
    fn apply_rule(&self, rule: &ValidationRule, row: &RowData) -> Option<ValidationError> {
        let field_value = row.data.get(&rule.field);

        match &rule.rule_type {
            crate::types::RuleType::Required => {
                let is_missing = match field_value {
                    None => true,
                    Some(serde_json::Value::Null) => true,
                    Some(serde_json::Value::String(s)) if s.trim().is_empty() => true,
                    _ => false,
                };
                if is_missing {
                    return Some(ValidationError {
                        row_index: row.index,
                        field: rule.field.clone(),
                        rule: rule.name.clone(),
                        message: format!("Field '{}' is required", rule.field),
                    });
                }
            }
            crate::types::RuleType::TypeCheck => {
                // Type checking logic
                if let Some(expected_type) = rule.params.get("type") {
                    if let Some(value) = field_value {
                        if !self.check_type(value, expected_type.as_str().unwrap_or("string")) {
                            return Some(ValidationError {
                                row_index: row.index,
                                field: rule.field.clone(),
                                rule: rule.name.clone(),
                                message: format!("Type mismatch for field '{}'", rule.field),
                            });
                        }
                    }
                }
            }
            crate::types::RuleType::Range => {
                // Range validation logic
                if let Some(value) = field_value {
                    // Try to get numeric value (either directly or by parsing string)
                    let num = value.as_f64().or_else(|| {
                        value.as_str().and_then(|s| s.parse::<f64>().ok())
                    });

                    if let Some(num) = num {
                        if let Some(min) = rule.params.get("min").and_then(|v| v.as_f64()) {
                            if num < min {
                                return Some(ValidationError {
                                    row_index: row.index,
                                    field: rule.field.clone(),
                                    rule: rule.name.clone(),
                                    message: format!("Value {} is below minimum {}", num, min),
                                });
                            }
                        }
                        if let Some(max) = rule.params.get("max").and_then(|v| v.as_f64()) {
                            if num > max {
                                return Some(ValidationError {
                                    row_index: row.index,
                                    field: rule.field.clone(),
                                    rule: rule.name.clone(),
                                    message: format!("Value {} exceeds maximum {}", num, max),
                                });
                            }
                        }
                    }
                }
            }
            crate::types::RuleType::Pattern => {
                // Regex pattern matching
                if let Some(value) = field_value {
                    if let Some(pattern) = rule.params.get("pattern").and_then(|v| v.as_str()) {
                        if let Ok(regex) = regex::Regex::new(pattern) {
                            let string_val = value.as_str().unwrap_or("");
                            if !regex.is_match(string_val) {
                                return Some(ValidationError {
                                    row_index: row.index,
                                    field: rule.field.clone(),
                                    rule: rule.name.clone(),
                                    message: format!("Value doesn't match pattern: {}", pattern),
                                });
                            }
                        }
                    }
                }
            }
            crate::types::RuleType::Length => {
                // String length validation
                if let Some(value) = field_value {
                    if let Some(string_val) = value.as_str() {
                        let len = string_val.len();
                        if let Some(min_len) = rule.params.get("min").and_then(|v| v.as_u64()) {
                            if len < min_len as usize {
                                return Some(ValidationError {
                                    row_index: row.index,
                                    field: rule.field.clone(),
                                    rule: rule.name.clone(),
                                    message: format!("Length {} is below minimum {}", len, min_len),
                                });
                            }
                        }
                        if let Some(max_len) = rule.params.get("max").and_then(|v| v.as_u64()) {
                            if len > max_len as usize {
                                return Some(ValidationError {
                                    row_index: row.index,
                                    field: rule.field.clone(),
                                    rule: rule.name.clone(),
                                    message: format!("Length {} exceeds maximum {}", len, max_len),
                                });
                            }
                        }
                    }
                }
            }
            crate::types::RuleType::Custom => {
                // Custom validation logic will be handled by Python callbacks
            }
        }

        None
    }

    fn check_type(&self, value: &serde_json::Value, expected_type: &str) -> bool {
        match expected_type {
            "string" => value.is_string(),
            "number" | "float" => {
                if value.is_number() {
                    return true;
                }
                // Try parsing string as number
                if let Some(s) = value.as_str() {
                    s.parse::<f64>().is_ok()
                } else {
                    false
                }
            }
            "integer" | "int" => {
                if value.is_i64() || value.is_u64() {
                    return true;
                }
                // Try parsing string as integer
                if let Some(s) = value.as_str() {
                    s.parse::<i64>().is_ok()
                } else {
                    false
                }
            }
            "boolean" | "bool" => {
                if value.is_boolean() {
                    return true;
                }
                // Try parsing string as boolean
                if let Some(s) = value.as_str() {
                    matches!(s.to_lowercase().as_str(), "true" | "false" | "1" | "0")
                } else {
                    false
                }
            }
            "null" => value.is_null(),
            _ => true,
        }
    }
}

impl ValidationResult {
    pub fn merge(&mut self, other: ValidationResult) {
        self.valid_count += other.valid_count;
        self.invalid_count += other.invalid_count;
        self.total_rows += other.total_rows;
        self.errors.extend(other.errors);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validation_result_merge() {
        let mut result1 = ValidationResult {
            valid_count: 10,
            invalid_count: 2,
            total_rows: 12,
            errors: vec![],
        };

        let result2 = ValidationResult {
            valid_count: 8,
            invalid_count: 1,
            total_rows: 9,
            errors: vec![],
        };

        result1.merge(result2);
        assert_eq!(result1.valid_count, 18);
        assert_eq!(result1.invalid_count, 3);
        assert_eq!(result1.total_rows, 21);
    }
}
