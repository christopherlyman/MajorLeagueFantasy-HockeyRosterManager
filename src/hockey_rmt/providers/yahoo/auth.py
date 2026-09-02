from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests


YAHOO_TOKEN_URL = (
    "https://api.login.yahoo.com/oauth2/get_token"
)


class YahooAuthError(RuntimeError):
    """Yahoo OAuth authentication failed."""


def _access_token_is_usable(
    *,
    access_token: str | None,
    expires_in: int | None,
    updated_at: datetime,
    now: datetime,
    refresh_margin_seconds: int,
) -> bool:
    if not access_token or not expires_in:
        return False

    expires_at = (
        updated_at
        + timedelta(seconds=int(expires_in))
    )

    refresh_at = (
        expires_at
        - timedelta(
            seconds=refresh_margin_seconds
        )
    )

    return now < refresh_at


def get_access_token(
    *,
    dsn: str,
    client_id: str,
    client_secret: str,
    token_key: str,
    refresh_margin_seconds: int = 300,
    session: requests.Session | None = None,
) -> str:
    if not dsn.strip():
        raise ValueError(
            "Postgres DSN must not be empty."
        )

    if not client_id.strip():
        raise ValueError(
            "Yahoo client ID must not be empty."
        )

    if not client_secret.strip():
        raise ValueError(
            "Yahoo client secret must not be empty."
        )

    key = token_key.strip()

    if not key:
        raise ValueError(
            "Yahoo token key must not be empty."
        )

    if refresh_margin_seconds < 0:
        raise ValueError(
            "Refresh margin must not be negative."
        )

    # Imported here so the provider module can still
    # be compiled/tested in environments that do not
    # have the Postgres driver installed.
    import psycopg

    http = session or requests.Session()
    now = datetime.now(timezone.utc)

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    refresh_token,
                    access_token,
                    token_type,
                    expires_in,
                    updated_at
                FROM public.yahoo_oauth_token
                WHERE app_name = %s
                FOR UPDATE
                """,
                (key,),
            )

            row = cur.fetchone()

            if row is None:
                raise YahooAuthError(
                    "No Yahoo OAuth token record "
                    f"exists for key {key!r}."
                )

            (
                refresh_token,
                access_token,
                token_type,
                expires_in,
                updated_at,
            ) = row

            if _access_token_is_usable(
                access_token=access_token,
                expires_in=expires_in,
                updated_at=updated_at,
                now=now,
                refresh_margin_seconds=(
                    refresh_margin_seconds
                ),
            ):
                return str(access_token)

            response = http.post(
                YAHOO_TOKEN_URL,
                auth=requests.auth.HTTPBasicAuth(
                    client_id,
                    client_secret,
                ),
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": (
                        refresh_token
                    ),
                },
                timeout=30,
            )

            if response.status_code != 200:
                raise YahooAuthError(
                    "Yahoo token refresh failed "
                    f"with HTTP "
                    f"{response.status_code}."
                )

            try:
                payload: dict[str, Any] = (
                    response.json()
                )
            except (
                requests.exceptions.JSONDecodeError
            ) as exc:
                raise YahooAuthError(
                    "Yahoo token endpoint "
                    "returned invalid JSON."
                ) from exc

            new_access_token = payload.get(
                "access_token"
            )

            if not new_access_token:
                raise YahooAuthError(
                    "Yahoo token response did not "
                    "contain an access token."
                )

            new_refresh_token = payload.get(
                "refresh_token",
                refresh_token,
            )

            new_token_type = payload.get(
                "token_type",
                token_type or "bearer",
            )

            new_expires_in = int(
                payload.get(
                    "expires_in",
                    3600,
                )
            )

            cur.execute(
                """
                UPDATE public.yahoo_oauth_token
                SET
                    refresh_token = %s,
                    access_token = %s,
                    token_type = %s,
                    expires_in = %s,
                    updated_at = now()
                WHERE app_name = %s
                """,
                (
                    new_refresh_token,
                    new_access_token,
                    new_token_type,
                    new_expires_in,
                    key,
                ),
            )

        conn.commit()

    return str(new_access_token)
