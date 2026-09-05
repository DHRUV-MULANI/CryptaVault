# CryptaVault Key Recovery Procedure (BIP-39 Mnemonic)

This guide documents the procedure for backing up and restoring master encryption keys using 24-word BIP-39 recovery phrases.

---

## 1. Zero-Knowledge Recovery Philosophy
In CryptaVault, the backend API and Supabase database **NEVER** hold your master password, recovery phrases, or unencrypted keys. If a user loses their master password and has not exported a recovery bundle, their data is mathematically unrecoverable.

The Recovery Bundle solves this by generating an offline cryptographic wrap of the user's master key:
- A 256-bit high-entropy seed is converted into a **24-word English mnemonic phrase**.
- The seed derives an ephemeral wrapping key via HKDF-SHA256.
- The master key is encrypted with **AES-256-GCM** and saved inside `recovery_bundle.json`.

---

## 2. Generating a Backup

Using the CryptaVault CLI:
```bash
cryptavault keys backup --output recovery_bundle.json
```

Or programmatically via Python:
```python
from cryptavault.keys.backup import KeyRecoveryManager

recovery_mgr = KeyRecoveryManager()
mnemonic_words, bundle = recovery_mgr.export_recovery_bundle(master_key_bytes)

print("WRITE DOWN THESE 24 WORDS ON PAPER:")
print(mnemonic_words)

with open("recovery_bundle.json", "w") as f:
    json.dump(bundle, f, indent=2)
```

> [!WARNING]
> Store the 24 words in a secure physical location (e.g. fireproof safe, paper vault). Never store the mnemonic phrase in cleartext on cloud note-taking services or unencrypted disks.

---

## 3. Restoring from a Recovery Bundle

To restore your vault:
```python
from cryptavault.keys.backup import KeyRecoveryManager

recovery_mgr = KeyRecoveryManager()
with open("recovery_bundle.json", "r") as f:
    bundle = json.load(f)

mnemonic_words = "your 24 words separated by spaces..."
recovered_master_key = recovery_mgr.import_recovery_bundle(mnemonic_words, bundle)
print(f"Master key recovered: {len(recovered_master_key)} bytes")
```
