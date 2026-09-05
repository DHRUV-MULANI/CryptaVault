#!/usr/bin/env bash
set -euo pipefail

# CryptaVault WASM Build Script
# Compiles packages/core into a Pyodide / WebAssembly distributable package

echo "==> Building CryptaVault WASM package..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

OUTPUT_DIR="${SCRIPT_DIR}/dist"
mkdir -p "${OUTPUT_DIR}"

echo "Target output: ${OUTPUT_DIR}"
echo "Checking Python build toolchain..."

# Build pure python wheel for Pyodide consumption
python3 -m pip install --upgrade build wheel
python3 -m build --wheel "${ROOT_DIR}/packages/core" --outdir "${OUTPUT_DIR}"

echo "==> WASM distribution artifact generated in ${OUTPUT_DIR}"
