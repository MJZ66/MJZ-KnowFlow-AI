"""Regression: PublishStatus must persist lowercase enum values for PostgreSQL."""

from app.models import PublishStatus


def test_publish_status_values_are_lowercase():
    assert PublishStatus.NONE.value == "none"
    assert PublishStatus.PENDING.value == "pending"
    assert PublishStatus.APPROVED.value == "approved"
    assert PublishStatus.REJECTED.value == "rejected"
