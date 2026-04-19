#!/bin/bash
echo "--- Running GitHub Actions Audit (zizmor) ---"
zizmor .

echo "--- Running Rust Security Audit (cargo audit) ---"
cargo audit # This checks your dependencies for known vulnerabilities