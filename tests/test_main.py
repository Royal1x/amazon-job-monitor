"""Small beginner-friendly tests for the Amazon job monitor helpers."""

import unittest
from datetime import datetime, timezone

import main


class MainHelpersTests(unittest.TestCase):
    """Check the small helper functions that power the monitor."""

    def test_format_target_locations(self) -> None:
        self.assertEqual(
            main.format_target_locations(),
            "Liverpool, NY, East Syracuse, NY",
        )

    def test_find_matching_location_for_liverpool(self) -> None:
        text = "Warehouse Associate opening in Liverpool, NY"
        self.assertEqual(main.find_matching_location(text), "Liverpool, NY")

    def test_find_matching_location_for_east_syracuse(self) -> None:
        text = "Fulfillment role in East Syracuse, New York"
        self.assertEqual(main.find_matching_location(text), "East Syracuse, NY")

    def test_find_matching_location_rejects_other_city(self) -> None:
        text = "Warehouse Associate opening in Rochester, NY"
        self.assertIsNone(main.find_matching_location(text))

    def test_looks_like_target_job_requires_location_and_keyword(self) -> None:
        self.assertTrue(
            main.looks_like_target_job(
                "Amazon warehouse associate in Liverpool, NY",
            )
        )
        self.assertFalse(
            main.looks_like_target_job(
                "Amazon customer service opening in Liverpool, NY",
            )
        )

    def test_build_job_id_uses_amazon_job_code_when_available(self) -> None:
        job_id = main.build_job_id(
            title="Warehouse Associate",
            location="Liverpool, NY",
            link="https://example.com/apply?jobId=JOB-US-1234567",
        )
        self.assertEqual(job_id, "JOB-US-1234567")

    def test_deduplicate_jobs_removes_duplicate_ids(self) -> None:
        jobs = [
            {"id": "job-1", "title": "A", "location": "Liverpool, NY", "link": "1"},
            {"id": "job-1", "title": "A again", "location": "Liverpool, NY", "link": "1"},
            {"id": "job-2", "title": "B", "location": "East Syracuse, NY", "link": "2"},
        ]
        deduplicated = main.deduplicate_jobs(jobs)
        self.assertEqual(len(deduplicated), 2)
        self.assertEqual([job["id"] for job in deduplicated], ["job-1", "job-2"])

    def test_format_syracuse_timestamp_uses_new_york_time(self) -> None:
        timestamp = main.format_syracuse_timestamp(
            datetime(2026, 1, 15, 15, 30, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(timestamp, "2026-01-15 10:30:00 AM EST")

    def test_split_recipients_handles_commas_and_spaces(self) -> None:
        recipients = main.split_recipients(" +13155551234, +13155550000 ,, ")
        self.assertEqual(recipients, ["+13155551234", "+13155550000"])


if __name__ == "__main__":
    unittest.main()
