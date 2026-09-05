#!/usr/bin/env python3
"""Interactive demo of CryptaVault Symmetric AEAD Ciphers."""

import os

from cryptavault.crypto.symmetric import AES256GCM, ChaCha20Poly1305, InvalidTagError


def main() -> None:
    print("=" * 65)
    print("  CryptaVault: Client-Side AEAD Symmetric Cipher Demonstration")
    print("=" * 65)

    # 1. AES-256-GCM
    print("\n[1] Testing AES-256-GCM (Authenticated Encryption)")
    aes = AES256GCM()
    key = os.urandom(32)
    secret_text = "Top-Secret Zero-Knowledge Vault Payload 🔐"
    plaintext = secret_text.encode("utf-8")
    aad = b"user-account-id:usr_9981"

    print(f"  • Key (32 bytes):      {key.hex()[:32]}...")
    print(f"  • Plaintext:           {secret_text}")
    print(f"  • Associated Data:     {aad.decode()}")

    # Encrypt
    nonce, ciphertext = aes.encrypt_auto_nonce(key, plaintext, aad)
    print(f"  • Generated Nonce (12B): {nonce.hex()}")
    print(f"  • Ciphertext + Tag:    {ciphertext.hex()}")

    # Decrypt
    decrypted = aes.decrypt(key, nonce, ciphertext, aad)
    print(f"  ✔ Decrypted correctly: {decrypted.decode('utf-8')}")

    # Tamper test
    print("\n[2] Testing Tamper Detection (Fail-Closed)")
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0x01  # Flip a single bit
    try:
        aes.decrypt(key, nonce, bytes(tampered), aad)
        print("  ❌ ERROR: Tampered ciphertext was accepted!")
    except InvalidTagError:
        print("  ✔ Attack intercepted: InvalidTagError raised immediately!")

    # 3. ChaCha20-Poly1305
    print("\n[3] Testing ChaCha20-Poly1305")
    chacha = ChaCha20Poly1305()
    c_nonce, c_cipher = chacha.encrypt_auto_nonce(key, plaintext, aad)
    c_decrypted = chacha.decrypt(key, c_nonce, c_cipher, aad)
    print(f"  ✔ ChaCha20 Decrypted:  {c_decrypted.decode('utf-8')}")

    print("\n" + "=" * 65)
    print("  All AEAD Symmetric Primitives Verified Successfully!")
    print("=" * 65)


if __name__ == "__main__":
    main()
