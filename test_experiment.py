import unittest

from experiment import HORIZONTAL, VERTICAL, ProbabilityReversalExperiment
from app import SUPABASE_FIELDS, build_supabase_record, reserve_participant_id


class ExperimentTests(unittest.TestCase):
    def test_participant_ids_are_unique_without_local_state(self):
        first = reserve_participant_id()
        second = reserve_participant_id()
        self.assertRegex(first, r"^participant_[0-9a-f]{32}$")
        self.assertNotEqual(first, second)

    def test_effective_probability_matches_shrew_formula(self):
        self.assertAlmostEqual(
            ProbabilityReversalExperiment.effective_probability(.2, 2), .488
        )

    def test_bait_persists_until_that_orientation_is_selected(self):
        exp = ProbabilityReversalExperiment(1, 1, reversal_every=0, seed=1)
        trial = exp.start_trial()
        self.assertTrue(trial.horizontal_baited and trial.vertical_baited)
        chosen = trial.left
        exp.choose("LEFT")
        if chosen == HORIZONTAL:
            self.assertFalse(exp.horizontal_baited)
            self.assertTrue(exp.vertical_baited)
        else:
            self.assertTrue(exp.horizontal_baited)
            self.assertFalse(exp.vertical_baited)

    def test_reversal_swaps_probabilities_and_resets_state(self):
        exp = ProbabilityReversalExperiment(.8, .2, reversal_every=1, seed=2)
        first = exp.start_trial()
        exp.choose("LEFT")
        second = exp.start_trial()
        self.assertFalse(first.reversed)
        self.assertTrue(second.reversed)
        self.assertEqual((second.horizontal_probability, second.vertical_probability), (.2, .8))
        self.assertEqual((second.horizontal_unchosen, second.vertical_unchosen), (0, 0))

    def test_timeout_does_not_change_counters(self):
        exp = ProbabilityReversalExperiment(.8, .2, reversal_every=0, seed=3)
        exp.start_trial()
        exp.timeout()
        self.assertEqual((exp.horizontal_unchosen, exp.vertical_unchosen), (0, 0))

    def test_supabase_record_is_allowlisted_and_normalized(self):
        payload = {field: "value" for field in SUPABASE_FIELDS}
        for field in (
            "block_number", "block_trial_number", "block_length", "favored_fruit",
            "favored_fruit_switched", "chosen_stimulus", "choice_clicked_at",
            "reaction_time_ms",
        ):
            payload[field] = ""
        for field in ("apple_baited", "banana_baited", "reward"):
            payload[field] = 1
        payload["not_a_database_column"] = "discard me"

        record = build_supabase_record(payload)

        self.assertNotIn("not_a_database_column", record)
        self.assertIsNone(record["block_number"])
        self.assertIsNone(record["favored_fruit_switched"])
        self.assertIs(record["reward"], True)

    def test_supabase_record_rejects_missing_fields(self):
        with self.assertRaisesRegex(ValueError, "Missing required fields"):
            build_supabase_record({})


if __name__ == "__main__":
    unittest.main()
