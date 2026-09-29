from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import httpx


class GroupIBError(Exception):
    pass


class GroupIBConfigurationError(GroupIBError):
    pass


class GroupIBAuthenticationError(GroupIBError):
    pass


class GroupIBRateLimitError(GroupIBError):
    pass


class GroupIBSchemaError(GroupIBError):
    pass


class GroupIBUnavailableError(GroupIBError):
    pass


@dataclass(frozen=True, slots=True)
class AccountGroupPage:
    count: int
    result_id: str | None
    items: tuple[Mapping[str, Any], ...]


class GroupIBClient:
    def __init__(self, username: str, api_token: str, *, base_url: str, timeout_seconds: float = 30.0) -> None:
        if not username.strip() or not api_token.strip():
            raise GroupIBConfigurationError("Group-IB credentials are not configured.")
        self._base_url = base_url.rstrip("/") + "/"
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            auth=(username.strip(), api_token.strip()),
            headers={"Accept": "application/json"},
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GroupIBClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_account_group_page(self, *, date_from: str, date_to: str, limit: int = 500, result_id: str | None = None) -> AccountGroupPage:
        if not 1 <= limit <= 500:
            raise ValueError("Group-IB limit must be between 1 and 500.")
        url = f"{self._base_url}compromised/account_group"
        params: dict[str, Any] = {"limit": limit}
        if result_id:
            params["resultId"] = result_id
        else:
            params.update({"df": date_from, "dt": date_to})
        try:
            response = self._client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise GroupIBUnavailableError("Unable to reach Group-IB.") from exc
        except httpx.HTTPError as exc:
            raise GroupIBUnavailableError("Unable to reach Group-IB.") from exc
        if response.status_code in (401, 403):
            raise GroupIBAuthenticationError("Unable to authenticate with Group-IB.")
        if response.status_code == 429:
            raise GroupIBRateLimitError("Group-IB API rate limit was reached.")
        if response.is_error:
            raise GroupIBUnavailableError("Unable to reach Group-IB.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise GroupIBSchemaError("Group-IB returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise GroupIBSchemaError("Group-IB response must be a JSON object.")
        count = payload.get("count")
        next_result_id = payload.get("resultId")
        items = payload.get("items")
        if not isinstance(count, int) or isinstance(count, bool):
            raise GroupIBSchemaError("Group-IB response field 'count' must be an integer.")
        if next_result_id is not None and not isinstance(next_result_id, str):
            raise GroupIBSchemaError("Group-IB response field 'resultId' must be a string.")
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise GroupIBSchemaError("Group-IB response field 'items' must be an array of objects.")
        return AccountGroupPage(count=count, result_id=next_result_id, items=tuple(items))
