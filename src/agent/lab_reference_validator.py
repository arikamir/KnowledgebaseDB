"""Bounded HTTPS-only validation for approved lab destinations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import ipaddress
import socket
from time import sleep
from urllib.parse import urljoin, urlparse


RETRYABLE_STATUSES = frozenset({408, 429})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class RetryableValidationError(RuntimeError):
    pass


class FinalValidationError(RuntimeError):
    pass


class InvalidTlsError(FinalValidationError):
    pass


@dataclass(frozen=True, slots=True)
class ValidationResponse:
    status_code: int
    headers: dict[str, str]


@dataclass(frozen=True, slots=True)
class LabValidationResult:
    result: str
    error_code: str | None
    status_code: int | None
    redirect_domains: tuple[str, ...]
    redirect_count: int
    attempts: int


@dataclass(slots=True)
class LabDestinationValidator:
    fetch: Callable[[str, float], ValidationResponse]
    resolve: Callable[[str], list[str]] = lambda host: list({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    sleeper: Callable[[float], None] = sleep
    timeout_seconds: float = 10.0
    max_redirects: int = 5
    max_attempts: int = 3

    def validate_reference(self, reference, approved_domains: set[str]) -> LabValidationResult:
        required = (
            reference.content_version, reference.provider_policy_version,
            reference.applicability_policy_version, reference.classifier_object_id,
            reference.classified_at,
        )
        if not all(required):
            return LabValidationResult("final_failure", "LAB_REFERENCE_PINS_INCOMPLETE", None, (), 0, 0)
        if reference.cost_status not in {"free", "paid", "subscription", "unknown"}:
            return LabValidationResult("final_failure", "LAB_COST_STATUS_INVALID", None, (), 0, 0)
        if reference.lab_required:
            if reference.omission_reason is not None or reference.omission_explanation is not None:
                return LabValidationResult("final_failure", "LAB_APPLICABILITY_INVALID", None, (), 0, 0)
        elif reference.omission_reason not in {"orientation", "conceptual_comparison", "review_only"} or not reference.omission_explanation or not 20 <= len(reference.omission_explanation.strip()) <= 500:
            return LabValidationResult("final_failure", "LAB_APPLICABILITY_INVALID", None, (), 0, 0)
        if reference.availability_state == "retired":
            return LabValidationResult("final_failure", "LAB_REFERENCE_RETIRED", None, (), 0, 0)
        return self.validate(reference.destination_url, approved_domains)

    def validate(self, destination_url: str, approved_domains: set[str]) -> LabValidationResult:
        last_code = "LAB_DESTINATION_UNAVAILABLE"
        last_status = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                status, domains = self._attempt(destination_url, approved_domains)
                return LabValidationResult("success", None, status, tuple(domains), len(domains), attempt)
            except FinalValidationError as error:
                return LabValidationResult("final_failure", str(error), getattr(error, "status_code", last_status), (), 0, attempt)
            except RetryableValidationError as error:
                last_code = str(error)
                last_status = getattr(error, "status_code", None)
                if attempt == self.max_attempts:
                    break
                retry_after = getattr(error, "retry_after", 0.0)
                self.sleeper(min(max(float(retry_after), 0.0), 60.0))
        return LabValidationResult("retryable_failure", last_code, last_status, (), 0, self.max_attempts)

    def _attempt(self, destination_url: str, approved_domains: set[str]) -> tuple[int, list[str]]:
        current = destination_url
        visited: set[str] = set()
        redirect_domains: list[str] = []
        for redirect_count in range(self.max_redirects + 1):
            normalized, hostname = self._guard_url(current, approved_domains)
            if normalized in visited:
                raise FinalValidationError("LAB_REDIRECT_LOOP")
            visited.add(normalized)
            try:
                response = self.fetch(normalized, self.timeout_seconds)
            except InvalidTlsError:
                raise
            except (TimeoutError, ConnectionError, OSError) as error:
                raise RetryableValidationError("LAB_DESTINATION_UNAVAILABLE") from error
            if 200 <= response.status_code < 300:
                return response.status_code, redirect_domains
            if response.status_code in REDIRECT_STATUSES:
                location = response.headers.get("location") or response.headers.get("Location")
                if not location:
                    raise FinalValidationError("LAB_REDIRECT_INVALID")
                if redirect_count >= self.max_redirects:
                    raise FinalValidationError("LAB_REDIRECT_LIMIT_EXCEEDED")
                current = urljoin(normalized, location)
                parsed = urlparse(current)
                if parsed.scheme != "https":
                    raise FinalValidationError("LAB_HTTPS_DOWNGRADE")
                redirect_domains.append((parsed.hostname or "").casefold())
                continue
            if response.status_code in RETRYABLE_STATUSES or 500 <= response.status_code <= 599:
                error = RetryableValidationError("LAB_DESTINATION_RETRYABLE_STATUS")
                error.status_code = response.status_code
                value = response.headers.get("retry-after") or response.headers.get("Retry-After")
                error.retry_after = float(value) if value and value.isdigit() else 0.0
                raise error
            error = FinalValidationError("LAB_DESTINATION_FINAL_STATUS")
            error.status_code = response.status_code
            raise error
        raise FinalValidationError("LAB_REDIRECT_LIMIT_EXCEEDED")

    def _guard_url(self, url: str, approved_domains: set[str]) -> tuple[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise FinalValidationError("LAB_DESTINATION_HTTPS_REQUIRED")
        hostname = parsed.hostname.casefold().rstrip(".")
        if hostname in {"localhost", "metadata.azure.internal"} or hostname.endswith((".local", ".internal", ".svc", ".cluster.local")):
            raise FinalValidationError("LAB_DESTINATION_INTERNAL")
        if not any(hostname == domain.casefold() or hostname.endswith(f".{domain.casefold()}") for domain in approved_domains):
            raise FinalValidationError("LAB_PROVIDER_DOMAIN_UNAPPROVED")
        try:
            addresses = self.resolve(hostname)
        except OSError as error:
            raise RetryableValidationError("LAB_DNS_UNAVAILABLE") from error
        if not addresses:
            raise RetryableValidationError("LAB_DNS_UNAVAILABLE")
        for value in addresses:
            address = ipaddress.ip_address(value)
            if not address.is_global or address.is_multicast or address.is_reserved or address.is_unspecified:
                raise FinalValidationError("LAB_DESTINATION_INTERNAL")
        normalized = parsed._replace(fragment="").geturl()
        return normalized, hostname
