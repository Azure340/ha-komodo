"""Tests for the release URL derivation helper."""

import pytest

from custom_components.komodo.data.service import derive_release_url


@pytest.mark.parametrize(
    "image,expected",
    [
        # ghcr.io images -> GitHub releases page
        ("ghcr.io/blakeblackshear/frigate:0.18.0-rc1", "https://github.com/blakeblackshear/frigate/releases"),
        ("ghcr.io/paperless-ngx/paperless-ngx:latest", "https://github.com/paperless-ngx/paperless-ngx/releases"),
        ("ghcr.io/moghtech/komodo-core:2", "https://github.com/moghtech/komodo-core/releases"),
        # docker hub images -> hub page
        ("adguard/adguardhome:latest", "https://hub.docker.com/r/adguard/adguardhome"),
        ("docker.io/ollama/ollama:latest", "https://hub.docker.com/r/ollama/ollama"),
        ("tailscale/tailscale:stable", "https://hub.docker.com/r/tailscale/tailscale"),
        # official images -> hub page
        ("redis:alpine", "https://hub.docker.com/_/redis"),
        ("mongo:7", "https://hub.docker.com/_/mongo"),
        # pinned digests are stripped
        ("ghcr.io/x/y@sha256:abc", "https://github.com/x/y/releases"),
        # registry host:port kept intact -> no match
        ("localhost:5000/x/y", None),
        # not enough info -> no URL
        (None, None),
        ("", None),
    ],
)
def test_derive_release_url(image, expected):
    assert derive_release_url(image) == expected
