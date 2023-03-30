from sentry.sentry_metrics.configuration import MetricPathKey
from sentry.sentry_metrics.indexer.mock import MockIndexer
from sentry.sentry_metrics.indexer.strings import SHARED_STRINGS
from sentry.snuba.metrics.naming_layer import SessionMRI

INDEXER = MockIndexer()


def test_resolve():
    assert INDEXER.resolve(MetricPathKey.RELEASE_HEALTH, 1, "what") is None
    assert (
        INDEXER.resolve(MetricPathKey.RELEASE_HEALTH, 1, SessionMRI.USER.value)
        == SHARED_STRINGS[SessionMRI.USER.value]
    )
    # hardcoded values don't depend on org_id
    assert (
        INDEXER.resolve(MetricPathKey.RELEASE_HEALTH, 0, SessionMRI.USER.value)
        == SHARED_STRINGS[SessionMRI.USER.value]
    )


def test_reverse_resolve():
    assert INDEXER.reverse_resolve(MetricPathKey.RELEASE_HEALTH, 1, 666) is None
    id = SHARED_STRINGS[SessionMRI.USER.value]
    assert INDEXER.reverse_resolve(MetricPathKey.RELEASE_HEALTH, 1, id) == SessionMRI.USER.value
