# Development Guide

## Prerequisites

- Python 3.8 or higher
- Rust 1.70 or higher
- Cargo
- Git

## Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/pyrustpipe.git
cd pyrustpipe
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Build Rust Extension

```bash
# Development build (faster, unoptimized)
maturin develop

# Release build (slower, optimized)
maturin develop --release
```

## Development Workflow

### Running Tests

```bash
# Python tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=pyrustpipe --cov-report=html

# Rust tests
cargo test

# All tests
cargo test && pytest tests/
```

### Code Quality

```bash
# Python formatting
black python/pyrustpipe

# Python linting
ruff check python/pyrustpipe

# Rust formatting
cargo fmt

# Rust linting
cargo clippy
```

### Building Documentation

```bash
# Python docs
cd docs
make html

# Rust docs
cargo doc --open
```

## Project Structure

```
pyrustpipe/
├── python/
│   └── pyrustpipe/        # Python package
│       ├── __init__.py
│       ├── schema.py      # Schema definitions
│       ├── validator.py   # Main validator
│       ├── decorators.py  # Rule decorators
│       ├── types.py       # Type definitions
│       └── cli.py         # CLI interface
├── src/                   # Rust source
│   ├── lib.rs            # PyO3 bindings
│   ├── types.rs          # Rust types
│   ├── validator.rs      # Validation engine
│   └── s3.rs             # S3 integration
├── tests/                # Python tests
├── examples/             # Usage examples
├── Cargo.toml           # Rust dependencies
├── pyproject.toml       # Python package config
└── README.md
```

## Making Changes

### Adding Python Features

1. Write code in `python/pyrustpipe/`
2. Add tests in `tests/`
3. Run tests: `pytest tests/`
4. Update documentation

### Adding Rust Features

1. Write code in `src/`
2. Add tests (inline or in `tests/` for integration)
3. Run tests: `cargo test`
4. Rebuild extension: `maturin develop`
5. Test Python integration

### Adding Examples

1. Create file in `examples/`
2. Use existing patterns from other examples
3. Test it works: `python examples/your_example.py`
4. Document in README

## Common Tasks

### Update Dependencies

```bash
# Python
pip install -U -e ".[dev]"

# Rust
cargo update
```

### Clean Build Artifacts

```bash
# Python
rm -rf build/ dist/ *.egg-info htmlcov/ .pytest_cache/

# Rust
cargo clean
```

### Profile Performance

```bash
# Python profiling
python -m cProfile -o profile.stats examples/benchmark.py
python -m pstats profile.stats

# Rust benchmarking
cargo bench
```

## CI/CD

Our CI pipeline runs on every push:

1. **Linting**: ruff, cargo clippy
2. **Formatting**: black, cargo fmt --check
3. **Tests**: pytest, cargo test
4. **Build**: maturin build

See `.github/workflows/ci.yml` for details.

## Release Process

1. Update version in `pyproject.toml` and `Cargo.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag v0.2.0`
4. Push: `git push origin v0.2.0`
5. Build wheels: `maturin build --release`
6. Publish: `maturin publish`

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/pyrustpipe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pyrustpipe/discussions)
- **Email**: your.email@example.com

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Tips

### Fast Development Iteration

```bash
# Terminal 1: Watch and rebuild on Rust changes
cargo watch -x 'build --lib'

# Terminal 2: Run Python tests
pytest tests/ -v --tb=short
```

### Debugging Rust from Python

Add print statements or use `dbg!()` macro in Rust code:

```rust
dbg!(&some_variable);
```

Then rebuild and run your Python script.

### Memory Profiling

```bash
# Python memory usage
python -m memory_profiler examples/large_dataset.py

# Rust memory usage
cargo build --release
valgrind target/release/pyrustpipe_core
```

## Architecture Decisions

### Why PyO3?

- **Best-in-class Python-Rust FFI**
- Active development and community
- Automatic Python type conversions
- Good error handling

### Why Rayon for Parallelism?

- Simple API (`.par_iter()`)
- Work-stealing scheduler
- No manual thread management
- Composable with iterators

### Why CSV Crate Instead of Polars?

- Lighter dependency
- Faster compilation
- Sufficient for MVP
- Can add Polars later for advanced features

## FAQ

**Q: Why can't I import pyrustpipe after installation?**  
A: Make sure you've run `maturin develop` to build the Rust extension.

**Q: Build fails with "cannot find -lpython"**  
A: Install Python development headers: `sudo apt-get install python3-dev`

**Q: AWS S3 operations fail**  
A: Configure AWS credentials: `aws configure` or set environment variables.

**Q: Tests pass but CLI doesn't work**  
A: Reinstall in editable mode: `pip install -e .`
