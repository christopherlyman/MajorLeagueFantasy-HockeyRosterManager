from __future__ import annotations

import unittest
from types import SimpleNamespace

import hockey_rmt.services.projection_adjustment as module


def _assignment(
    category: str,
    group: str,
):
    return SimpleNamespace(
        category_identifier=category,
        group_identifier=group,
    )


def _deployment(
    *assignments,
):
    return SimpleNamespace(
        full_name="Test Player",
        assignments=tuple(
            assignments
        ),
    )


class DfoDeploymentAmbiguityTests(
    unittest.TestCase
):
    def test_pp1_pp2_ambiguity_is_neutral_not_no_pp(
        self,
    ):
        deployment = _deployment(
            _assignment(
                module.CATEGORY_EVEN_STRENGTH,
                "f3",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp1",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp2",
            ),
        )

        (
            factor,
            ev_group,
            pp_group,
            reasons,
        ) = module._deployment_factor(
            deployment
        )

        self.assertEqual(
            ev_group,
            "f3",
        )

        self.assertIsNone(
            pp_group
        )

        self.assertAlmostEqual(
            factor,
            1.0
            + module._DFO_EV_EFFECT[
                "f3"
            ],
        )

        self.assertIn(
            "dfo_pp_ambiguous:pp1,pp2:neutral",
            reasons,
        )

        self.assertFalse(
            any(
                reason.startswith(
                    "dfo_pp:none:"
                )
                for reason in reasons
            )
        )

        self.assertFalse(
            any(
                reason.startswith(
                    "dfo_pp:pp1:"
                )
                for reason in reasons
            )
        )

        self.assertFalse(
            any(
                reason.startswith(
                    "dfo_pp:pp2:"
                )
                for reason in reasons
            )
        )

    def test_pp1_pp2_policy_is_order_independent(
        self,
    ):
        deployment = _deployment(
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp2",
            ),
            _assignment(
                module.CATEGORY_EVEN_STRENGTH,
                "f3",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp1",
            ),
        )

        (
            _,
            _,
            pp_group,
            reasons,
        ) = module._deployment_factor(
            deployment
        )

        self.assertIsNone(
            pp_group
        )

        self.assertIn(
            "dfo_pp_ambiguous:pp1,pp2:neutral",
            reasons,
        )

    def test_other_multi_pp_combination_still_fails_closed(
        self,
    ):
        deployment = _deployment(
            _assignment(
                module.CATEGORY_EVEN_STRENGTH,
                "f2",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp1",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp3",
            ),
        )

        with self.assertRaisesRegex(
            module.ProjectionAdjustmentError,
            "multiple power-play groups",
        ):
            module._deployment_factor(
                deployment
            )

    def test_multiple_even_strength_groups_still_fail_closed(
        self,
    ):
        deployment = _deployment(
            _assignment(
                module.CATEGORY_EVEN_STRENGTH,
                "f2",
            ),
            _assignment(
                module.CATEGORY_EVEN_STRENGTH,
                "f3",
            ),
            _assignment(
                module.CATEGORY_POWER_PLAY,
                "pp1",
            ),
        )

        with self.assertRaisesRegex(
            module.ProjectionAdjustmentError,
            "multiple even-strength groups",
        ):
            module._deployment_factor(
                deployment
            )


if __name__ == "__main__":
    unittest.main()
