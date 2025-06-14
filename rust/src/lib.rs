use pyo3::prelude::*;

#[pyfunction]
fn hello() -> PyResult<String> {
    Ok("Hello from Rust!".to_string())
}

// Updated for PyO3 0.20 (use &PyModule instead of Bound)
#[pymodule]
fn pyrustpipe(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}