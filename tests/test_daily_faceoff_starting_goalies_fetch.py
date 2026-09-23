from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

import requests

import hockey_rmt.providers.daily_faceoff.starting_goalies as module


GAME_DATE = date(
    2026,
    3,
    14,
)


class _Response:
    def __init__(
        self,
        *,
        status_code: int,
        text: str = "<html></html>",
    ):
        self.status_code = status_code
        self.text = text


class _Session:
    def __init__(
        self,
        response=None,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    def get(
        self,
        url,
        *,
        timeout,
        headers,
    ):
        self.calls.append(
            {
                "url": url,
                "timeout": timeout,
                "headers": headers,
            }
        )

        if self.error is not None:
            raise self.error

        return self.response


class StartingGoalieFetchTests(
    unittest.TestCase
):
    def test_fetch_uses_date_url_headers_timeout_and_parser(
        self,
    ):
        session = _Session(
            response=_Response(
                status_code=200,
                text="provider-html",
            )
        )

        sentinel = (
            object(),
        )

        with patch.object(
            module,
            "parse_starting_goalies_page",
            return_value=sentinel,
        ) as parser:
            result = (
                module.fetch_starting_goalies(
                    GAME_DATE,
                    session=session,
                    timeout_seconds=12.5,
                )
            )

        self.assertIs(
            result,
            sentinel,
        )

        self.assertEqual(
            len(session.calls),
            1,
        )

        call = session.calls[0]

        self.assertEqual(
            call["url"],
            module.starting_goalies_url(
                GAME_DATE
            ),
        )

        self.assertEqual(
            call["timeout"],
            12.5,
        )

        self.assertTrue(
            call["headers"].get(
                "User-Agent"
            )
        )

        parser.assert_called_once_with(
            "provider-html",
            expected_date=GAME_DATE,
        )

    def test_non_200_fails_closed(
        self,
    ):
        session = _Session(
            response=_Response(
                status_code=503,
            )
        )

        with self.assertRaisesRegex(
            module.DailyFaceoffStartingGoaliesError,
            "HTTP 503",
        ):
            module.fetch_starting_goalies(
                GAME_DATE,
                session=session,
            )

    def test_transport_failure_is_provider_error(
        self,
    ):
        session = _Session(
            error=requests.Timeout(
                "timeout"
            )
        )

        with self.assertRaisesRegex(
            module.DailyFaceoffStartingGoaliesError,
            "request failed",
        ):
            module.fetch_starting_goalies(
                GAME_DATE,
                session=session,
            )


if __name__ == "__main__":
    unittest.main()
