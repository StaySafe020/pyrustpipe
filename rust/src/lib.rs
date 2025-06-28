use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct FieldSchema {
    #[serde(rename = "type")]
    type_name: String,
    required: bool,
}

#[derive(Serialize, Deserialize)]
struct Schema {
    fields: HashMap<String, FieldSchema>,
}

#[pyclass]
#[derive(Serialize)]
struct ValidationError {
    #[pyo3(get)]
    field: String,
    #[pyo3(get)]
    message: String,
}

#[pymethods]
impl ValidationError {
    #[new]
    fn new(field: String, message: String) -> Self {
        ValidationError { field, message }
    }

    fn __str__(&self) -> String {
        format!("{}: {}", self.field, self.message)
    }
}

#[pyfunction]
fn validate(schema_json: String, data_json: String) -> PyResult<Vec<Vec<ValidationError>>> {
    let schema: Schema = serde_json::from_str(&schema_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid schema JSON: {}", e))
    })?;
    let data: Vec<Value> = serde_json::from_str(&data_json).map_err(|e| {
        PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid data JSON: {}", e))
    })?;
    let mut results = Vec::new();

    for record in data {
        let mut errors = Vec::new();
        let obj = match record.as_object() {
            Some(obj) => obj,
            None => {
                results.push(vec![ValidationError::new(
                    "".to_string(),
                    "Record is not an object".to_string(),
                )]);
                continue;
            }
        };

        for (field_name, field_schema) in &schema.fields {
            let value = obj.get(field_name);
            if field_schema.required && value.is_none() {
                errors.push(ValidationError::new(
                    field_name.clone(),
                    "Required field missing".to_string(),
                ));
                continue;
            }

            if let Some(value) = value {
                let is_valid = match field_schema.type_name.as_str() {
                    "int" => value.is_i64(),
                    "str" => value.is_string(),
                    _ => false,
                };
                if !is_valid {
                    errors.push(ValidationError::new(
                        field_name.clone(),
                        format!("Expected type {}", field_schema.type_name),
                    ));
                }
            }
        }
        results.push(errors);
    }
    Ok(results)
}

#[pymodule]
fn pyrustpipe(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_class::<ValidationError>()?;
    m.add_function(wrap_pyfunction!(validate, m)?)?;
    Ok(())
}