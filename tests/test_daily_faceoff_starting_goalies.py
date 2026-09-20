from __future__ import annotations

import json
import unittest
from datetime import date, timezone
from pathlib import Path

from hockey_rmt.domain.goalie_start import (
    GOALIE_START_CONFIRMED,
    GOALIE_START_LIKELY,
    GOALIE_START_SOURCE_DAILY_FACEOFF,
    GOALIE_START_UNCONFIRMED,
)
from hockey_rmt.providers.daily_faceoff.starting_goalies import (
    DailyFaceoffStartingGoaliesError,
    parse_starting_goalies_page,
    starting_goalies_url,
)


FIXTURE = (
    Path(__file__)
    .parent
    / "fixtures"
    / "daily_faceoff"
    / "starting_goalies_contract.html"
)


class DailyFaceoffStartingGoaliesTests(
    unittest.TestCase
):
    def _fixture_text(
        self,
    ) -> str:
        return FIXTURE.read_text(
            encoding="utf-8"
        )

    def _payload(
        self,
    ) -> dict:
        html_text = (
            self._fixture_text()
        )

        marker = (
            '<script id="__NEXT_DATA__" '
            'type="application/json">'
        )

        raw = (
            html_text
            .split(
                marker,
                1,
            )[1]
            .split(
                "</script>",
                1,
            )[0]
        )

        return json.loads(
            raw
        )

    def _html_for_payload(
        self,
        payload: dict,
    ) -> str:
        return (
            "<!doctype html>"
            "<html><head>"
            '<script id="__NEXT_DATA__" '
            'type="application/json">'
            + json.dumps(
                payload
            )
            + "</script>"
            "</head><body></body></html>"
        )

    def test_url_is_date_scoped(
        self,
    ) -> None:
        self.assertEqual(
            starting_goalies_url(
                date(
                    2026,
                    3,
                    14,
                )
            ),
            (
                "https://www.dailyfaceoff.com/"
                "starting-goalies/2026-03-14"
            ),
        )

    def test_parses_confirmed_likely_and_unconfirmed(
        self,
    ) -> None:
        rows = parse_starting_goalies_page(
            self._fixture_text(),
            expected_date=date(
                2026,
                3,
                14,
            ),
        )

        self.assertEqual(
            len(rows),
            4,
        )

        by_name = {
            row.goalie_name: row
            for row in rows
        }

        ullmark = by_name[
            "Linus Ullmark"
        ]

        self.assertEqual(
            ullmark.source,
            GOALIE_START_SOURCE_DAILY_FACEOFF,
        )
        self.assertEqual(
            ullmark.start_state,
            GOALIE_START_CONFIRMED,
        )
        self.assertTrue(
            ullmark.is_home
        )
        self.assertEqual(
            ullmark.provider_goalie_id,
            2534,
        )
        self.assertEqual(
            ullmark.provider_team_id,
            21,
        )
        self.assertEqual(
            ullmark.team_name,
            "Ottawa Senators",
        )
        self.assertEqual(
            ullmark.opponent_team_name,
            "Anaheim Ducks",
        )
        self.assertEqual(
            ullmark.game_time_utc.tzinfo,
            timezone.utc,
        )
        self.assertIsNotNone(
            ullmark.evidence_created_at_utc
        )
        self.assertEqual(
            ullmark.evidence_source_name,
            "TSN1200",
        )

        vasilevskiy = by_name[
            "Andrei Vasilevskiy"
        ]

        self.assertEqual(
            vasilevskiy.start_state,
            GOALIE_START_LIKELY,
        )

        bussi = by_name[
            "Brandon Bussi"
        ]

        self.assertEqual(
            bussi.start_state,
            GOALIE_START_UNCONFIRMED,
        )
        self.assertIsNone(
            bussi.evidence_created_at_utc
        )
        self.assertIsNone(
            bussi.evidence_source_name
        )
        self.assertIsNone(
            bussi.evidence_source_url
        )

    def test_unknown_non_null_status_fails_closed(
        self,
    ) -> None:
        payload = self._payload()

        payload[
            "props"
        ][
            "pageProps"
        ][
            "data"
        ][0][
            "homeNewsStrengthName"
        ] = "Probable"

        with self.assertRaisesRegex(
            DailyFaceoffStartingGoaliesError,
            "Unrecognized Daily Faceoff goalie",
        ):
            parse_starting_goalies_page(
                self._html_for_payload(
                    payload
                ),
                expected_date=date(
                    2026,
                    3,
                    14,
                ),
            )

    def test_wrong_game_date_fails(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            DailyFaceoffStartingGoaliesError,
            "did not match requested date",
        ):
            parse_starting_goalies_page(
                self._fixture_text(),
                expected_date=date(
                    2026,
                    3,
                    15,
                ),
            )

    def test_missing_next_data_fails(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            DailyFaceoffStartingGoaliesError,
            "Expected exactly one",
        ):
            parse_starting_goalies_page(
                "<html></html>",
                expected_date=date(
                    2026,
                    3,
                    14,
                ),
            )

    def test_partial_goalie_identity_fails(
        self,
    ) -> None:
        payload = self._payload()

        payload[
            "props"
        ][
            "pageProps"
        ][
            "data"
        ][0][
            "homeGoalieId"
        ] = None

        with self.assertRaisesRegex(
            DailyFaceoffStartingGoaliesError,
            "goalie identity was partial",
        ):
            parse_starting_goalies_page(
                self._html_for_payload(
                    payload
                ),
                expected_date=date(
                    2026,
                    3,
                    14,
                ),
            )


if __name__ == "__main__":
    unittest.main()
