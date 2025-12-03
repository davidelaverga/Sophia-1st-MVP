import logging

from app.obs.metrics import EMOTIONAL_SKILL_IDS, skill_total, track_skill_distribution


def test_track_skill_distribution_warns_on_unknown_skill(caplog):
    caplog.set_level(logging.WARNING)
    initial_labels = {
        sample.labels.get("skill_id") for sample in skill_total.collect()[0].samples
    }

    track_skill_distribution("NOT_A_SKILL")

    warnings = [
        rec for rec in caplog.records if "Unknown emotional skill_id" in rec.message
    ]
    assert warnings
    updated_labels = {
        sample.labels.get("skill_id") for sample in skill_total.collect()[0].samples
    }
    # No new labels should be registered
    assert updated_labels == initial_labels == set(EMOTIONAL_SKILL_IDS)
