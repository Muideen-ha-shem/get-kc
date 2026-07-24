"""Tests for the SSL chain-repair helpers used by PageFetcher.

These tests cover the pure/offline parts of ``ssl_chain_repair`` — exception
unwrapping and the incomplete-chain classification — without making real
network calls. The end-to-end repair flow (fetching a real leaf certificate,
resolving its AIA URL, verifying the repaired chain) is exercised manually
against live domains (e.g. badssl.com's ``incomplete-chain`` test host) since
it inherently requires network access and real CA infrastructure.
"""

from __future__ import annotations

import ssl

import pytest

from src.services.retrievers.ssl_chain_repair import (
    find_ssl_verification_error,
    is_incomplete_chain_error,
)


def _make_verify_error(verify_code: int, verify_message: str = "test") -> ssl.SSLCertVerificationError:
    err = ssl.SSLCertVerificationError()
    err.verify_code = verify_code
    err.verify_message = verify_message
    return err


class TestFindSslVerificationError:
    def test_finds_direct_ssl_error(self):
        err = _make_verify_error(20)
        assert find_ssl_verification_error(err) is err

    def test_finds_ssl_error_via_cause_chain(self):
        ssl_err = _make_verify_error(20)
        wrapped_once = ConnectionError("wrapped")
        wrapped_once.__cause__ = ssl_err
        wrapped_twice = RuntimeError("outer")
        wrapped_twice.__cause__ = wrapped_once

        assert find_ssl_verification_error(wrapped_twice) is ssl_err

    def test_finds_ssl_error_via_context_chain(self):
        ssl_err = _make_verify_error(20)
        wrapped = ConnectionError("wrapped")
        wrapped.__context__ = ssl_err

        assert find_ssl_verification_error(wrapped) is ssl_err

    def test_returns_none_when_no_ssl_error_present(self):
        plain = ConnectionError("just a plain connection error")
        assert find_ssl_verification_error(plain) is None

    def test_does_not_infinite_loop_on_cyclical_cause(self):
        a = RuntimeError("a")
        b = RuntimeError("b")
        a.__cause__ = b
        b.__cause__ = a  # cycle

        # Must terminate rather than looping forever.
        assert find_ssl_verification_error(a) is None


class TestIsIncompleteChainError:
    @pytest.mark.parametrize("code", [2, 20, 21])
    def test_incomplete_chain_codes_are_repairable(self, code):
        assert is_incomplete_chain_error(_make_verify_error(code)) is True

    @pytest.mark.parametrize("code", [10, 18, 19, 23, 62])
    def test_other_verification_failures_are_not_repairable(self, code):
        # 10 = expired, 18/19 = self-signed, 23 = revoked, 62 = hostname mismatch
        assert is_incomplete_chain_error(_make_verify_error(code)) is False

    def test_missing_verify_code_is_not_repairable(self):
        err = ssl.SSLCertVerificationError()
        assert is_incomplete_chain_error(err) is False
