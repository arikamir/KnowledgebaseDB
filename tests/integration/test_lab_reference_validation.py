import pytest

from agent.lab_reference_validator import InvalidTlsError, LabDestinationValidator, ValidationResponse


class Fetch:
    def __init__(self, outcomes): self.outcomes = list(outcomes); self.calls = []
    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException): raise outcome
        return outcome


OK = ValidationResponse(200, {})
GLOBAL = lambda _host: ["8.8.8.8"]


def test_direct_and_approved_redirect_success_use_ten_second_timeout_and_five_hop_budget():
    fetch = Fetch([ValidationResponse(302, {"Location": "https://cdn.labs.example.com/start"}), OK])
    result = LabDestinationValidator(fetch, resolve=GLOBAL).validate("https://labs.example.com", {"labs.example.com"})
    assert result.result == "success" and result.redirect_domains == ("cdn.labs.example.com",) and result.redirect_count == 1
    assert fetch.calls == [("https://labs.example.com", 10.0), ("https://cdn.labs.example.com/start", 10.0)]


@pytest.mark.parametrize("outcome", [TimeoutError(), ConnectionError(), OSError(), ValidationResponse(408, {}), ValidationResponse(429, {}), ValidationResponse(500, {}), ValidationResponse(503, {})])
def test_retryable_failures_make_initial_plus_at_most_two_attempts(outcome):
    fetch = Fetch([outcome, outcome, outcome])
    result = LabDestinationValidator(fetch, resolve=GLOBAL, sleeper=lambda _delay: None).validate("https://labs.example.com", {"labs.example.com"})
    assert result.result == "retryable_failure" and result.attempts == 3 and len(fetch.calls) == 3


def test_retry_after_is_capped_at_sixty_seconds():
    sleeps = []
    fetch = Fetch([ValidationResponse(429, {"Retry-After": "999"})] * 3)
    LabDestinationValidator(fetch, resolve=GLOBAL, sleeper=sleeps.append).validate("https://labs.example.com", {"labs.example.com"})
    assert sleeps == [60.0, 60.0]


@pytest.mark.parametrize(
    "url,domains,outcome,error",
    [
        ("http://labs.example.com", {"labs.example.com"}, OK, "HTTPS_REQUIRED"),
        ("https://evil.example.net", {"labs.example.com"}, OK, "DOMAIN_UNAPPROVED"),
        ("https://metadata.azure.internal", {"metadata.azure.internal"}, OK, "DESTINATION_INTERNAL"),
        ("https://service.cluster.local", {"service.cluster.local"}, OK, "DESTINATION_INTERNAL"),
        ("https://labs.example.com", {"labs.example.com"}, ValidationResponse(404, {}), "FINAL_STATUS"),
        ("https://labs.example.com", {"labs.example.com"}, InvalidTlsError("LAB_TLS_INVALID"), "TLS_INVALID"),
    ],
)
def test_final_policy_and_protocol_failures_do_not_retry(url, domains, outcome, error):
    fetch = Fetch([outcome])
    result = LabDestinationValidator(fetch, resolve=GLOBAL).validate(url, domains)
    assert result.result == "final_failure" and error in result.error_code and result.attempts == 1


@pytest.mark.parametrize("address", ["10.0.0.1", "127.0.0.1", "169.254.169.254", "224.0.0.1"])
def test_private_link_local_metadata_and_non_global_resolutions_are_final(address):
    result = LabDestinationValidator(Fetch([OK]), resolve=lambda _host: [address]).validate("https://labs.example.com", {"labs.example.com"})
    assert result.result == "final_failure" and result.error_code == "LAB_DESTINATION_INTERNAL"


def test_redirect_loop_downgrade_unapproved_destination_and_more_than_five_hops_are_final():
    loop = Fetch([ValidationResponse(302, {"Location": "https://labs.example.com"})])
    assert LabDestinationValidator(loop, resolve=GLOBAL).validate("https://labs.example.com", {"labs.example.com"}).error_code == "LAB_REDIRECT_LOOP"
    downgrade = Fetch([ValidationResponse(302, {"Location": "http://labs.example.com"})])
    assert LabDestinationValidator(downgrade, resolve=GLOBAL).validate("https://labs.example.com", {"labs.example.com"}).error_code == "LAB_HTTPS_DOWNGRADE"
    unapproved = Fetch([ValidationResponse(302, {"Location": "https://evil.example.net"})])
    assert LabDestinationValidator(unapproved, resolve=GLOBAL).validate("https://labs.example.com", {"labs.example.com"}).error_code == "LAB_PROVIDER_DOMAIN_UNAPPROVED"
    redirects = [ValidationResponse(302, {"Location": f"https://labs.example.com/{index}"}) for index in range(1, 7)]
    result = LabDestinationValidator(Fetch(redirects), resolve=GLOBAL).validate("https://labs.example.com", {"labs.example.com"})
    assert result.error_code == "LAB_REDIRECT_LIMIT_EXCEEDED"
