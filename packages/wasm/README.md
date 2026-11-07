# @cryptavault/wasm

Packaging scaffold for running the Python core in a Pyodide/WebAssembly context.

Current behavior: `build.sh` builds a pure-Python wheel of `packages/core` into `dist/` for Pyodide consumption. It does not yet compile the Rust/C extension set or expose a JavaScript binding. The deployed web portal uses the native Web Crypto implementation in `packages/web/src/lib/crypto.ts` instead.

```bash
./packages/wasm/build.sh
```

Do not describe this package as a completed WASM cryptography runtime until a Pyodide bundle and JavaScript bridge are implemented and tested.
