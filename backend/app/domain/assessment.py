from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from uuid import uuid4

from app.domain.classification import Classification
from app.domain.normalization import CanonicalIntelligenceRecord


class ActivityLevel(StrEnum):
    NONE_OBSERVED = "NONE_OBSERVED"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AssessmentConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    assessment_id: str
    run_id: str
    activity_level: ActivityLevel
    confidence: AssessmentConfidence
    facts: tuple[str, ...]
    key_observations: tuple[str, ...]
    assessment: str
    recommended_analyst_attention: tuple[str, ...]
    assessment_basis: tuple[str, ...]

    def json_fields(self) -> dict[str, str]:
        return {
            "facts": json.dumps(self.facts, ensure_ascii=False),
            "observations": json.dumps(self.key_observations, ensure_ascii=False),
            "recommended_attention": json.dumps(self.recommended_analyst_attention, ensure_ascii=False),
            "basis": json.dumps(self.assessment_basis, ensure_ascii=False),
        }


def _count_new(classifications: list[Classification]) -> int:
    return sum(item is Classification.NEW for item in classifications)


def _activity_level(new_count: int, affected_domains: int) -> ActivityLevel:
    if new_count == 0:
        return ActivityLevel.NONE_OBSERVED
    if new_count <= 2 and affected_domains <= 1:
        return ActivityLevel.LOW
    if new_count <= 5 and affected_domains <= 3:
        return ActivityLevel.MODERATE
    if new_count <= 10 and affected_domains <= 5:
        return ActivityLevel.HIGH
    return ActivityLevel.CRITICAL


def _confidence(*, normalization_warnings: int, baseline_available: bool, record_count: int) -> AssessmentConfidence:
    if normalization_warnings == 0 and baseline_available:
        return AssessmentConfidence.HIGH
    if record_count == 0 or normalization_warnings > max(1, record_count):
        return AssessmentConfidence.LOW
    return AssessmentConfidence.MEDIUM


def build_assessment(
    *,
    run_id: str,
    records: list[CanonicalIntelligenceRecord],
    classifications: list[Classification],
    normalization_warnings: int,
    baseline_available: bool,
    evaluated_at: datetime | None = None,
) -> AssessmentResult:
    if len(records) != len(classifications):
        raise ValueError("records and classifications must have the same length.")
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    new_records = [record for record, classification in zip(records, classifications) if classification is Classification.NEW]
    domains = sorted({record.victim_domain for record in new_records if record.victim_domain})
    malware = sorted({family for record in new_records for family in record.stealer_families})
    sources = sorted({source for record in new_records for source in record.source_names if source})
    ips = sorted({ip for record in new_records for ip in record.victim_ips})
    new_count = len(new_records)
    level = _activity_level(new_count, len(domains))
    confidence = _confidence(
        normalization_warnings=normalization_warnings,
        baseline_available=baseline_available,
        record_count=len(records),
    )

    facts = (
        f"Evaluation time: {evaluated_at.astimezone(timezone.utc).isoformat()}",
        f"Records evaluated: {len(records)}",
        f"NEW compromises observed: {new_count}",
        f"Affected victim domains in NEW records: {len(domains)}",
        f"Infostealer families in NEW records: {len(malware)}",
        f"Victim IPs in NEW records: {len(ips)}",
    )
    observations = []
    if domains:
        observations.append("NEW activity affected domains: " + ", ".join(domains))
    if malware:
        observations.append("NEW records contain infostealer families: " + ", ".join(malware))
    if sources:
        observations.append("NEW records include sources: " + ", ".join(sources))
    if not observations:
        observations.append("No NEW compromise records were observed in this run.")
        observations.append("Absence of observed NEW intelligence is not evidence that the environment is free of compromise.")

    if new_count == 0:
        assessment_text = "The run did not identify NEW compromise records under the configured seven-day classification policy."
    else:
        assessment_text = (
            f"The run identified {new_count} NEW compromise record(s) under the configured seven-day policy, "
            f"covering {len(domains)} affected domain(s). This assessment is limited to the Group-IB intelligence "
            "observed and classified during this run."
        )

    attention = []
    if new_count:
        attention.append("Review each NEW compromised account and validate the affected identity with the corresponding domain owner.")
        attention.append("Prioritize credential reset and session/token invalidation according to the affected service's incident procedure.")
        if malware:
            attention.append("Review endpoint telemetry for the observed infostealer family or families.")
        if ips:
            attention.append("Correlate the observed victim IPs with available endpoint, identity, and network telemetry.")
    else:
        attention.append("Continue routine monitoring; do not interpret the absence of NEW Group-IB records as proof of no compromise.")
    if normalization_warnings:
        attention.append(f"Review {normalization_warnings} normalization warning(s) before treating the dataset as complete.")

    basis = (
        "Deterministic rules only; no LLM-generated assessment.",
        "NEW is limited to previously unknown identities with a usable provider compromise/detection timeline inside seven days.",
        "Known identities are classified as REPEAT or RESEEN_RECYCLED from durable identity and observation fingerprint state.",
        f"Normalization warnings recorded: {normalization_warnings}",
        f"Previous baseline available: {baseline_available}",
    )

    return AssessmentResult(
        assessment_id=str(uuid4()),
        run_id=run_id,
        activity_level=level,
        confidence=confidence,
        facts=facts,
        key_observations=tuple(observations),
        assessment=assessment_text,
        recommended_analyst_attention=tuple(attention),
        assessment_basis=basis,
    )
