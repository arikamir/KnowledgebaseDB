import pytest

from storage.database import PersistenceUnavailable, PostgresEntraConnectionFactory


def test_entra_connection_retries_at_exact_intervals_and_refreshes_token():
    tokens = iter(["token-1", "token-2", "token-3"])
    attempts = []
    sleeps = []

    def connect(token):
        attempts.append(token)
        if len(attempts) < 3:
            raise ConnectionError("postgres unavailable")
        return "connected"

    factory = PostgresEntraConnectionFactory(lambda: next(tokens), connect, sleeps.append)
    assert factory() == "connected"
    assert attempts == ["token-1", "token-2", "token-3"]
    assert sleeps == [0.25, 1.0]


def test_persistent_failure_maps_to_stable_code_and_never_returns_partial_connection():
    factory = PostgresEntraConnectionFactory(lambda: "fresh-token", lambda _: (_ for _ in ()).throw(ConnectionError()), lambda _: None)
    with pytest.raises(PersistenceUnavailable, match="PERSISTENCE_UNAVAILABLE"):
        factory()


def test_token_acquisition_failure_uses_same_retry_budget():
    calls = []

    def acquire():
        calls.append(True)
        raise RuntimeError("identity unavailable")

    factory = PostgresEntraConnectionFactory(acquire, lambda _: None, lambda _: None)
    with pytest.raises(PersistenceUnavailable):
        factory()
    assert len(calls) == 3
