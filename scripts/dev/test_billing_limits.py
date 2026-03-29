import unittest
from types import SimpleNamespace

from app.services.billing import resolve_effective_limits


class BillingLimitsTests(unittest.TestCase):
    def test_user_override_negative_is_unlimited(self):
        user = SimpleNamespace(limit_overrides={"entries_per_day": -1, "stt_seconds_per_day": -1})
        effective = resolve_effective_limits(user, {"entries_per_day": 5, "stt_seconds_per_day": 600})
        self.assertTrue(effective["entries_unlimited"])
        self.assertTrue(effective["stt_unlimited"])
        self.assertEqual(effective["source"], "user_override")

    def test_legacy_keys_supported(self):
        user = SimpleNamespace(limit_overrides={"entries_count": 10, "stt_seconds": 1200})
        effective = resolve_effective_limits(user, {"entries_per_day": 5, "stt_seconds_per_day": 600})
        self.assertEqual(effective["entries_per_day"], 10)
        self.assertEqual(effective["stt_seconds_per_day"], 1200)

    def test_default_plan_used_without_override(self):
        user = SimpleNamespace(limit_overrides=None)
        effective = resolve_effective_limits(user, {"entries_per_day": 7, "stt_seconds_per_day": 700})
        self.assertEqual(effective["entries_per_day"], 7)
        self.assertEqual(effective["stt_seconds_per_day"], 700)
        self.assertEqual(effective["source"], "plan_or_default")


if __name__ == "__main__":
    unittest.main()
