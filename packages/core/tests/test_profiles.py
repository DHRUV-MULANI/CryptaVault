"""Tests for CryptaVault security profiles and registry mappings."""

import cryptavault  # noqa: F401
import pytest
from cryptavault.adaptive.profiles import (
    SecurityLevel,
    SecurityProfile,
    get_profile,
    list_profiles,
)
from cryptavault.plugins.registry import (
    encryption_registry,
    hash_registry,
    kem_registry,
)


def test_list_profiles() -> None:
    """Ensure all 4 security tiers are defined and returned."""
    profiles = list_profiles()
    assert len(profiles) == 4
    levels = {p.level for p in profiles}
    assert levels == {
        SecurityLevel.PERFORMANCE,
        SecurityLevel.BALANCED,
        SecurityLevel.HIGH,
        SecurityLevel.MAXIMUM,
    }


def test_get_profile_by_enum_and_string() -> None:
    """Ensure lookup works case-insensitively and by enum."""
    p1 = get_profile(SecurityLevel.PERFORMANCE)
    p2 = get_profile("performance")
    p3 = get_profile("PERFORMANCE")

    assert p1 == p2 == p3
    assert p1.symmetric_cipher == "aes-256-gcm"
    assert p1.chunk_size_bytes == 4 * 1024 * 1024


def test_invalid_profile_raises() -> None:
    """Looking up an invalid profile name raises ValueError."""
    with pytest.raises(ValueError, match="Unknown security profile"):
        get_profile("ULTRA_SECRET_UNKNOWN")


def test_profiles_map_to_valid_plugin_registries() -> None:
    """Ensure all symmetric ciphers, hashes, and KEMs in the profiles are registered."""
    for profile in list_profiles():
        assert isinstance(profile, SecurityProfile)

        # Check symmetric cipher exists in encryption_registry
        assert profile.symmetric_cipher in encryption_registry.list_available()

        # Check hash algorithm exists in hash_registry
        assert profile.hash_algorithm in hash_registry.list_available()

        # Check KEM exists in kem_registry
        assert profile.kem_algorithm in kem_registry.list_available()
