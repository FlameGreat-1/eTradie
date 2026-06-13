"""EA identity verification.

The engine asks the EA `EA_IDENTITY` after every fresh authenticated
connection. The reply carries the EA's runtime identity:
  - magic_number    : the MAGIC_NUMBER input on the EA
  - account_login   : MT5 account this terminal is logged in to
  - account_server  : broker server name
  - account_company : broker company string
  - terminal_build  : MT5 terminal build number
  - ea_version      : EA #property version
  - zmq_port        : the port the EA bound to
  - started_at      : UTC unix timestamp of EA OnInit

The verifier compares these against the values the engine stored in
broker_connections (login, server). On mismatch it raises
EAIdentityMismatchError, which the connection manager catches and
disables the connection (kill-switch).

The verifier is pure logic: callers fetch the EA reply and pass it
in. This keeps the module trivially unit-testable.

Audit ref: CHECKLIST Section 4 - 'Detect EA vs backend signal
mismatch' + 'Kill-switch if EA diverges from expected logic'.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.shared.exceptions import EAIdentityMismatchError
from engine.shared.logging import get_logger
from engine.shared.metrics.prometheus import (
    BROKER_EA_IDENTITY_MISMATCH_TOTAL,
    BROKER_EA_IDENTITY_TOTAL,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExpectedEAIdentity:
    """What the engine expects from the EA for this connection.

    Each field is optional - the verifier only checks fields that
    are set. magic_number=0 is a sentinel for 'engine has not
    configured an expected magic', meaning any magic is accepted.
    Same convention for the others. This avoids forcing a tight
    coupling between connection-create flow and identity-verify flow
    at the database level; the engine can begin verifying as soon
    as expected values are populated.
    """

    magic_number: int = 0
    account_login: str = ""
    account_server: str = ""
    minimum_ea_version: str = ""


@dataclass(frozen=True)
class EAIdentitySnapshot:
    """Parsed EA_IDENTITY reply."""

    magic_number: int
    account_login: str
    account_server: str
    account_company: str
    account_name: str
    terminal_build: int
    ea_version: str
    zmq_port: int
    started_at: int

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EAIdentitySnapshot:
        return cls(
            magic_number=int(raw.get("magic_number", 0) or 0),
            account_login=str(raw.get("account_login", "")).strip(),
            account_server=str(raw.get("account_server", "")).strip(),
            account_company=str(raw.get("account_company", "")).strip(),
            account_name=str(raw.get("account_name", "")).strip(),
            terminal_build=int(raw.get("terminal_build", 0) or 0),
            ea_version=str(raw.get("ea_version", "")).strip(),
            zmq_port=int(raw.get("zmq_port", 0) or 0),
            started_at=int(raw.get("started_at", 0) or 0),
        )


class EAIdentityVerifier:
    """Verifies EA_IDENTITY against expected values.

    Constructed per (provider, account_id) so the Prometheus labels
    on emitted metrics carry the right tenant.
    """

    def __init__(self, *, provider: str, account_id: str) -> None:
        self.provider = provider
        self.account_id = account_id or "unknown"

    def verify(
        self,
        observed: EAIdentitySnapshot,
        expected: ExpectedEAIdentity,
    ) -> None:
        """Raise EAIdentityMismatchError on any divergence.

        The check is field-by-field. A single mismatched field is
        sufficient to disable the connection: a wrong magic means
        positions the engine adopts would carry the wrong identity;
        a wrong account_login means the operator wired the EA to a
        different MT5 account than the one stored in the connection
        row.
        """
        mismatches: dict[str, tuple[Any, Any]] = {}

        if expected.magic_number not in (0, observed.magic_number):
            mismatches["magic"] = (expected.magic_number, observed.magic_number)

        if expected.account_login and observed.account_login != expected.account_login:
            mismatches["login"] = (expected.account_login, observed.account_login)

        if expected.account_server and observed.account_server != expected.account_server:
            mismatches["server"] = (expected.account_server, observed.account_server)

        if (
            expected.minimum_ea_version
            and observed.ea_version
            and _version_tuple(observed.ea_version) < _version_tuple(expected.minimum_ea_version)
        ):
            mismatches["ea_version"] = (
                expected.minimum_ea_version,
                observed.ea_version,
            )

        if mismatches:
            for field in mismatches:
                BROKER_EA_IDENTITY_MISMATCH_TOTAL.labels(
                    provider=self.provider,
                    account_id=self.account_id,
                    field=field,
                ).inc()
            BROKER_EA_IDENTITY_TOTAL.labels(
                provider=self.provider,
                account_id=self.account_id,
                result="mismatch",
            ).inc()
            logger.error(
                "ea_identity_mismatch",
                extra={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "mismatches": {k: {"expected": v[0], "observed": v[1]} for k, v in mismatches.items()},
                },
            )
            raise EAIdentityMismatchError(
                "EA identity does not match expected values; connection will be disabled",
                details={
                    "provider": self.provider,
                    "account_id": self.account_id,
                    "mismatches": {k: {"expected": v[0], "observed": v[1]} for k, v in mismatches.items()},
                },
            )

        BROKER_EA_IDENTITY_TOTAL.labels(
            provider=self.provider,
            account_id=self.account_id,
            result="match",
        ).inc()
        logger.info(
            "ea_identity_match",
            extra={
                "provider": self.provider,
                "account_id": self.account_id,
                "magic": observed.magic_number,
                "login": observed.account_login,
                "server": observed.account_server,
                "terminal_build": observed.terminal_build,
                "ea_version": observed.ea_version,
            },
        )


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse 'X.Y.Z' (or 'X.Y') into a tuple for ordering. Non-numeric
    suffixes are dropped; missing parts default to 0.
    """
    parts: list[int] = []
    for raw in version.split("."):
        digits = ""
        for ch in raw:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])
