"""Test-scope compatibility shim for aioresponses + aiohttp 3.14.

aiohttp 3.14 made ``stream_writer`` a required keyword-only argument of
``aiohttp.ClientResponse.__init__``. The pinned ``aioresponses==0.7.8``
(the latest published release) constructs ``ClientResponse`` without
passing ``stream_writer``, so every mocked request raised::

    TypeError: ClientResponse.__init__() missing 1 required keyword-only
    argument: 'stream_writer'

aiohttp cannot be downgraded (3.14.0 is a security pin enforced by
``pip-audit --strict``; some CVEs are only fixed in 3.14), and there is
no newer aioresponses release. The compatibility gap is therefore
bridged here, in test scope only: an autouse fixture wraps
``ClientResponse.__init__`` so that when ``stream_writer`` is absent it
is filled with a no-op writer, then the original constructor is
restored. Production code is untouched.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import aiohttp
import pytest

_ORIGINAL_CLIENT_RESPONSE_INIT = aiohttp.ClientResponse.__init__
_STREAM_WRITER_PARAM = "stream_writer"

# Only install the shim when the running aiohttp actually requires the
# kwarg, so the tests keep working unchanged on older/newer aiohttp.
_REQUIRES_STREAM_WRITER = _STREAM_WRITER_PARAM in inspect.signature(
    _ORIGINAL_CLIENT_RESPONSE_INIT
).parameters


def _patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    if _STREAM_WRITER_PARAM not in kwargs:
        kwargs[_STREAM_WRITER_PARAM] = MagicMock()
    return _ORIGINAL_CLIENT_RESPONSE_INIT(self, *args, **kwargs)


@pytest.fixture(autouse=True)
def _aioresponses_stream_writer_compat(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a default ``stream_writer`` for aioresponses-built responses.

    No-op on aiohttp versions that do not require the kwarg.
    """
    if not _REQUIRES_STREAM_WRITER:
        return
    monkeypatch.setattr(aiohttp.ClientResponse, "__init__", _patched_init)
