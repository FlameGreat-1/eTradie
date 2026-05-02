"""MetaAPI Provisioning API client.

Handles the full lifecycle of provisioning MT5 trading accounts
in the MetaApi cloud:

  1. provision_account()  — Create a cloud MT5 connection from user credentials
  2. get_account_status()  — Poll deployment/connection state
  3. deploy_account()      — (Re-)deploy a previously undeployed account
  4. undeploy_account()    — Undeploy (stop cloud instance, stop billing)
  5. delete_account()      — Permanently remove the cloud account

Uses the PLATFORM-LEVEL MetaAPI token (MT5_METAAPI_TOKEN env var).
Each user provides their own MT5 broker credentials (login, password, server)
and the provisioner creates a unique cloud account_id per user.

Reference: https://metaapi.cloud/docs/provisioning/api/account/createAccount/
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Optional

from engine.shared.exceptions import (
    ConfigurationError,
    ProviderAuthenticationError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from engine.shared.http.client import HttpClient
from engine.shared.logging import get_logger

logger = get_logger(__name__)

# MetaAPI Provisioning API base URL.
_PROVISIONING_BASE_URL = (
    "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"
)

# Maximum number of polling attempts when MetaAPI returns 202 (async).
_MAX_POLL_ATTEMPTS = 30

# Seconds to wait between polling attempts.
_POLL_INTERVAL_SECONDS = 5

# MetaAPI error codes mapped to user-friendly messages.
_ERROR_MESSAGES: dict[str, str] = {
    "E_SRV_NOT_FOUND": (
        "MT5 server not found. Please check your server name is correct. "
        "Ensure it matches exactly what your broker provides "
        "(e.g. 'ICMarketsSC-Demo', 'Exness-MT5Trial9')."
    ),
    "E_AUTH": (
        "Authentication failed. Please verify your MT5 login number "
        "and password are correct. Make sure you are using your "
        "trading password (not the investor/read-only password)."
    ),
    "E_SERVER_TIMEZONE": (
        "Could not detect broker server settings. Please try again "
        "in a few minutes. If the issue persists, contact support."
    ),
    "E_RESOURCE_SLOTS": (
        "Your trading account requires additional cloud resources. "
        "Please contact support for assistance."
    ),
    "E_NO_SYMBOLS": (
        "No trading symbols found on your account. Please ensure "
        "your broker account is active and has symbols configured."
    ),
    "ERR_OTP_REQUIRED": (
        "Your account requires one-time password (OTP) authentication. "
        "Please disable OTP via the MetaTrader mobile app, or use "
        "a different account."
    ),
    "E_PASSWORD_CHANGE_REQUIRED": (
        "Your broker requires you to change your MT5 password. "
        "Please change it in MetaTrader and try again."
    ),
    "E_TRADING_ACCOUNT_DISABLED": (
        "Your broker reports this trading account is disabled. "
        "Please contact your broker or use a different account."
    ),
}


class MetaApiProvisioner:
    """Provisions and manages MT5 cloud accounts via MetaAPI.

    This service uses the platform-level MetaAPI developer token
    (from MT5_METAAPI_TOKEN env var) to create cloud MT5 connections
    for individual users who provide their MT5 broker credentials.

    Each provisioned account gets a unique account_id from MetaAPI,
    which is stored in the broker_connections database table.
    """

    def __init__(
        self,
        http_client: HttpClient,
        platform_token: str,
        magic_number: int = 0,
    ) -> None:
        """Initialize the provisioner.

        Args:
            http_client: Shared HTTP client with circuit breaker / retries.
            platform_token: MetaAPI developer API token (platform-level).
            magic_number: MT5 magic number for all provisioned accounts.
        """
        if not platform_token:
            raise ConfigurationError(
                "MT5_METAAPI_TOKEN is required for MetaAPI provisioning",
                details={"hint": "Set MT5_METAAPI_TOKEN in your .env file"},
            )
        self._http = http_client
        self._token = platform_token
        self._magic = magic_number
        self._auth_headers = {"auth-token": platform_token}

    # -- Public API -----------------------------------------------------------

    async def provision_account(
        self,
        *,
        login: str,
        password: str,
        server: str,
        name: str,
    ) -> dict[str, Any]:
        """Provision a new MT5 cloud account.

        Calls MetaAPI's Provisioning API to create a cloud MT5 connection
        using the user's broker credentials. Handles both synchronous
        (201) and asynchronous (202) responses.

        Args:
            login: MT5 account login number (e.g. "435112187").
            password: MT5 trading password.
            server: MT5 broker server name (e.g. "Exness-MT5Trial9").
            name: Human-readable name for the account.

        Returns:
            Dict with keys:
                - account_id: str — MetaAPI account UUID
                - state: str — Account state ("DEPLOYED", etc.)

        Raises:
            ProviderAuthenticationError: Invalid MT5 credentials.
            ProviderResponseError: MetaAPI returned an error.
            ProviderUnavailableError: MetaAPI is unreachable.
            ProviderError: Other provisioning errors.
        """
        payload: dict[str, Any] = {
            "login": str(login),
            "password": password,
            "name": name,
            "server": server,
            "platform": "mt5",
        }

        if self._magic:
            payload["magic"] = self._magic

        # Generate a unique transaction ID for idempotency (32-char hex required).
        transaction_id = uuid.uuid4().hex
        headers = {
            **self._auth_headers,
            "transaction-id": transaction_id,
        }

        logger.info(
            "metaapi_provisioning_start",
            extra={
                "server": server,
                "login": login,
                "name": name,
                "transaction_id": transaction_id,
            },
        )

        try:
            return await self._create_with_polling(
                payload=payload,
                headers=headers,
                transaction_id=transaction_id,
            )
        except ProviderError:
            raise
        except Exception as exc:
            logger.error(
                "metaapi_provisioning_unexpected_error",
                extra={"error": str(exc), "login": login, "server": server},
                exc_info=True,
            )
            raise ProviderError(
                f"Unexpected provisioning error: {exc}",
                details={"login": login, "server": server},
            ) from exc

    async def get_account_status(
        self,
        account_id: str,
    ) -> dict[str, Any]:
        """Get the current state/status of a provisioned account.

        Args:
            account_id: MetaAPI account UUID.

        Returns:
            Dict with account details including 'state' and 'connectionStatus'.
        """
        url = f"{_PROVISIONING_BASE_URL}/users/current/accounts/{account_id}"
        try:
            result = await self._http.get(
                url,
                provider_name="metaapi_provisioning",
                category="account_status",
                headers=self._auth_headers,
                timeout_override=30,
            )
            if not isinstance(result, dict):
                raise ProviderResponseError(
                    "Invalid response from MetaAPI provisioning API",
                    details={"account_id": account_id},
                )
            return result
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                f"Failed to get account status: {exc}",
                details={"account_id": account_id},
            ) from exc

    async def deploy_account(self, account_id: str) -> bool:
        """Deploy (or re-deploy) a cloud account.

        Args:
            account_id: MetaAPI account UUID.

        Returns:
            True if the deploy request was accepted.
        """
        url = (
            f"{_PROVISIONING_BASE_URL}"
            f"/users/current/accounts/{account_id}/deploy"
        )
        try:
            await self._http.post(
                url,
                json_body={},
                provider_name="metaapi_provisioning",
                category="deploy",
                headers=self._auth_headers,
                timeout_override=30,
            )
            logger.info(
                "metaapi_account_deployed",
                extra={"account_id": account_id},
            )
            return True
        except Exception as exc:
            logger.error(
                "metaapi_deploy_failed",
                extra={"account_id": account_id, "error": str(exc)},
            )
            raise ProviderError(
                f"Failed to deploy account: {exc}",
                details={"account_id": account_id},
            ) from exc

    async def undeploy_account(self, account_id: str) -> bool:
        """Undeploy a cloud account (stops the cloud instance).

        Args:
            account_id: MetaAPI account UUID.

        Returns:
            True if the undeploy request was accepted.
        """
        url = (
            f"{_PROVISIONING_BASE_URL}"
            f"/users/current/accounts/{account_id}/undeploy"
        )
        try:
            await self._http.post(
                url,
                json_body={},
                provider_name="metaapi_provisioning",
                category="undeploy",
                headers=self._auth_headers,
                timeout_override=30,
            )
            logger.info(
                "metaapi_account_undeployed",
                extra={"account_id": account_id},
            )
            return True
        except Exception as exc:
            logger.warning(
                "metaapi_undeploy_failed",
                extra={"account_id": account_id, "error": str(exc)},
            )
            # Non-fatal: account may already be undeployed.
            return False

    async def delete_account(self, account_id: str) -> bool:
        """Permanently delete a cloud account from MetaAPI.

        Should be called after undeploy. Removes all cloud resources
        and stops billing for this account.

        Args:
            account_id: MetaAPI account UUID.

        Returns:
            True if deletion was successful.
        """
        url = (
            f"{_PROVISIONING_BASE_URL}"
            f"/users/current/accounts/{account_id}"
        )
        try:
            await self._http.delete(
                url,
                provider_name="metaapi_provisioning",
                category="delete",
                headers=self._auth_headers,
                timeout_override=30,
            )
            logger.info(
                "metaapi_account_deleted",
                extra={"account_id": account_id},
            )
            return True
        except Exception as exc:
            logger.warning(
                "metaapi_delete_failed",
                extra={"account_id": account_id, "error": str(exc)},
            )
            # Non-fatal: account may already be deleted.
            return False

    async def cleanup_account(self, account_id: str) -> None:
        """Undeploy and then delete a cloud account.

        Called when a user deletes a broker connection.
        Best-effort: logs warnings but does not raise on failure.
        """
        logger.info(
            "metaapi_cleanup_start",
            extra={"account_id": account_id},
        )
        await self.undeploy_account(account_id)
        # Brief pause to let the undeploy propagate.
        await asyncio.sleep(2)
        await self.delete_account(account_id)

    # -- Internal helpers -----------------------------------------------------

    async def _create_with_polling(
        self,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
        transaction_id: str,
    ) -> dict[str, Any]:
        """Create account with 202/async polling support.

        MetaAPI may return:
          - 201: Account created immediately
          - 202: Async processing; poll with same transaction-id
          - 4xx: Validation/auth error
        """
        url = f"{_PROVISIONING_BASE_URL}/users/current/accounts"

        for attempt in range(1, _MAX_POLL_ATTEMPTS + 1):
            try:
                result = await self._http.post(
                    url,
                    json_body=payload,
                    provider_name="metaapi_provisioning",
                    category="provision",
                    headers=headers,
                    timeout_override=120,
                )
            except Exception as exc:
                self._handle_error(exc, payload)
                # _handle_error always raises, but just in case:
                raise

            if not isinstance(result, dict):
                raise ProviderResponseError(
                    "Invalid provisioning response",
                    details={"result": str(result)[:200]},
                )

            # Check for success: response has an 'id' field.
            account_id = result.get("id")
            if account_id:
                state = result.get("state", "UNKNOWN")
                logger.info(
                    "metaapi_provisioning_success",
                    extra={
                        "account_id": account_id,
                        "state": state,
                        "attempt": attempt,
                        "login": payload.get("login"),
                        "server": payload.get("server"),
                    },
                )
                return {
                    "account_id": account_id,
                    "state": state,
                }

            # If we get a message but no id, it's likely a 202 async response.
            message = result.get("message", "")
            if "retry" in message.lower() or "progress" in message.lower():
                logger.info(
                    "metaapi_provisioning_polling",
                    extra={
                        "attempt": attempt,
                        "message": message[:200],
                        "login": payload.get("login"),
                    },
                )
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                continue

            # Check for error response.
            error = result.get("error")
            if error:
                details = result.get("details", "")
                self._raise_for_error_code(
                    details if isinstance(details, str) else "",
                    result,
                    payload,
                )

            # Unknown response format.
            raise ProviderResponseError(
                f"Unexpected provisioning response: {result}",
                details={"response": str(result)[:500]},
            )

        raise ProviderUnavailableError(
            "MetaAPI provisioning timed out after maximum polling attempts",
            details={
                "max_attempts": _MAX_POLL_ATTEMPTS,
                "login": payload.get("login"),
                "server": payload.get("server"),
            },
        )

    def _handle_error(
        self,
        exc: Exception,
        payload: dict[str, Any],
    ) -> None:
        """Map HTTP/transport errors to domain-specific exceptions."""
        error_str = str(exc)

        # Try to extract MetaAPI error code from the exception message.
        for code, message in _ERROR_MESSAGES.items():
            if code in error_str:
                if code == "E_AUTH":
                    raise ProviderAuthenticationError(
                        message,
                        details={
                            "login": payload.get("login"),
                            "server": payload.get("server"),
                            "metaapi_code": code,
                        },
                    ) from exc
                raise ProviderResponseError(
                    message,
                    details={
                        "login": payload.get("login"),
                        "server": payload.get("server"),
                        "metaapi_code": code,
                    },
                ) from exc

        # Check for E_SRV_NOT_FOUND with suggested servers.
        if "E_SRV_NOT_FOUND" in error_str:
            raise ProviderResponseError(
                _ERROR_MESSAGES["E_SRV_NOT_FOUND"],
                details={
                    "login": payload.get("login"),
                    "server": payload.get("server"),
                    "metaapi_code": "E_SRV_NOT_FOUND",
                    "raw_error": error_str[:500],
                },
            ) from exc

        # Generic provisioning error.
        raise ProviderError(
            f"MetaAPI provisioning failed: {error_str}",
            details={
                "login": payload.get("login"),
                "server": payload.get("server"),
            },
        ) from exc

    def _raise_for_error_code(
        self,
        error_code: str,
        full_response: dict[str, Any],
        payload: dict[str, Any],
    ) -> None:
        """Raise the appropriate exception for a MetaAPI error code."""
        # Check dict-style details (e.g. {"code": "E_SRV_NOT_FOUND", ...}).
        details = full_response.get("details")
        if isinstance(details, dict):
            code = details.get("code", "")
            if code in _ERROR_MESSAGES:
                error_code = code

        message = _ERROR_MESSAGES.get(
            error_code,
            f"MetaAPI error: {full_response.get('message', 'Unknown error')}",
        )

        if error_code == "E_AUTH":
            raise ProviderAuthenticationError(
                message,
                details={
                    "login": payload.get("login"),
                    "server": payload.get("server"),
                    "metaapi_code": error_code,
                },
            )

        raise ProviderResponseError(
            message,
            details={
                "login": payload.get("login"),
                "server": payload.get("server"),
                "metaapi_code": error_code,
                "raw_response": str(full_response)[:500],
            },
        )
