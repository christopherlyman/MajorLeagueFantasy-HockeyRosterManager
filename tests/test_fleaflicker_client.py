from __future__ import annotations

import unittest

from hockey_rmt.providers.fleaflicker.client import (
    FLEAFLICKER_API_BASE_URL,
    FleaflickerApiError,
    FleaflickerClient,
)


class _Response:
    def __init__(
        self,
        *,
        status_code: int = 200,
        payload=None,
    ) -> None:
        self.status_code = status_code
        self._payload = (
            {}
            if payload is None
            else payload
        )

    def json(self):
        return self._payload


class _Session:
    def __init__(
        self,
        response: _Response,
    ) -> None:
        self.response = response
        self.headers = {}
        self.calls = []

    def get(
        self,
        url,
        *,
        params,
        timeout,
    ):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )

        return self.response


class FleaflickerClientTests(unittest.TestCase):
    def test_get_json_uses_official_api_endpoint(
        self,
    ):
        session = _Session(
            _Response(
                payload={
                    "season": 2026,
                }
            )
        )

        client = FleaflickerClient(
            timeout_seconds=17,
            session=session,
        )

        payload = client.get_json(
            "FetchLeagueStandings",
            params={
                "sport": "NHL",
                "league_id": "12090",
            },
        )

        self.assertEqual(
            payload,
            {
                "season": 2026,
            },
        )

        self.assertEqual(
            session.calls,
            [
                {
                    "url": (
                        FLEAFLICKER_API_BASE_URL
                        + "/FetchLeagueStandings"
                    ),
                    "params": {
                        "sport": "NHL",
                        "league_id": "12090",
                    },
                    "timeout": 17,
                }
            ],
        )

        self.assertEqual(
            session.headers["Accept"],
            "application/json",
        )

    def test_non_200_fails(
        self,
    ):
        client = FleaflickerClient(
            session=_Session(
                _Response(
                    status_code=503,
                )
            )
        )

        with self.assertRaisesRegex(
            FleaflickerApiError,
            "HTTP 503",
        ):
            client.get_json(
                "FetchLeagueRules",
            )

    def test_empty_endpoint_fails(
        self,
    ):
        client = FleaflickerClient(
            session=_Session(
                _Response()
            )
        )

        with self.assertRaises(ValueError):
            client.get_json("   ")

    def test_non_positive_timeout_fails(
        self,
    ):
        with self.assertRaises(ValueError):
            FleaflickerClient(
                timeout_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
