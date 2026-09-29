from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
from typing import Any, Mapping
from urllib.parse import urlparse


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _object(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _objects(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(dict.fromkeys(item.strip() for item in value if isinstance(item, str) and item.strip()))


def _unique(values: list[str | None]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _parse_utc(value: Any) -> tuple[datetime | None, str | None]:
    raw = _text(value)
    if raw is None:
        return None, None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, "invalid_datetime"
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc), None


def _parse_ip(value: Any) -> str | None:
    candidate = _text(value)
    if candidate is None:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _valid_url(value: Any) -> str | None:
    candidate = _text(value)
    if candidate is None:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return candidate
    return None


def _canonical_date_pair(item: Mapping[str, Any], events: tuple[Mapping[str, Any], ...]) -> tuple[datetime | None, datetime | None, list[str]]:
    warnings: list[str] = []
    first, w = _parse_utc(item.get("dateFirstCompromised"))
    if w: warnings.append("invalid_dateFirstCompromised")
    last, w = _parse_utc(item.get("dateLastCompromised"))
    if w: warnings.append("invalid_dateLastCompromised")
    compromised, w = _parse_utc(item.get("dateCompromised") or item.get("compromisedAt"))
    if w: warnings.append("invalid_dateCompromised")
    if first is None and compromised is not None: first = compromised
    if last is None and compromised is not None: last = compromised
    event_dates: list[datetime] = []
    for event in events:
        for key in ("dateCompromised", "compromisedAt", "dateFirstCompromised", "dateLastCompromised"):
            parsed, warning = _parse_utc(event.get(key))
            if warning: warnings.append(f"invalid_event_{key}")
            if parsed is not None: event_dates.append(parsed)
    if event_dates:
        first = min([first, *event_dates]) if first is not None else min(event_dates)
        last = max([last, *event_dates]) if last is not None else max(event_dates)
    return first, last, list(dict.fromkeys(warnings))


@dataclass(frozen=True, slots=True)
class CanonicalIntelligenceRecord:
    provider: str
    provider_record_id: str | None
    compromise_identity: str
    account: str | None
    username: str | None
    password: str | None
    victim_domain: str | None
    compromised_date: datetime | None
    last_compromised_date: datetime | None
    date_detected: datetime | None
    first_seen: datetime | None
    last_seen: datetime | None
    event_count: int
    stealer_families: tuple[str, ...]
    malware_ids: tuple[str, ...]
    victim_ips: tuple[str, ...]
    victim_countries: tuple[str, ...]
    victim_cities: tuple[str, ...]
    victim_providers: tuple[str, ...]
    target_urls: tuple[str, ...]
    source_types: tuple[str, ...]
    source_ids: tuple[str, ...]
    source_names: tuple[str, ...]
    source_links: tuple[str, ...]
    threat_actors: tuple[str, ...]
    service_domain: str | None
    service_host: str | None
    service_url: str | None
    login_url: str | None
    event_ids: tuple[str, ...]
    credential_present: bool
    observation_fingerprint: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=lambda value: value.isoformat())


def _fallback_identity(*, account: str | None, domain: str | None, first_seen: datetime | None,
                       last_seen: datetime | None, source_types: tuple[str, ...],
                       event_ids: tuple[str, ...]) -> str:
    material = {
        "account": account, "domain": domain,
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "source_types": source_types, "event_ids": event_ids,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def normalize_record(item: Mapping[str, Any], *, provider: str = "groupib") -> CanonicalIntelligenceRecord:
    if not isinstance(item, Mapping):
        raise TypeError("Group-IB record must be an object.")
    warnings: list[str] = []
    events = _objects(item.get("events"))
    parsed_login = _object(item.get("parsedLogin"))
    service = _object(item.get("service"))
    provider_record_id = _text(item.get("id"))
    account = _text(item.get("login"))
    password = _text(item.get("password")) or next((_text(e.get("password")) for e in events if _text(e.get("password"))), None)
    domain = _text(parsed_login.get("domain"))
    compromised_date, last_compromised_date, date_warnings = _canonical_date_pair(item, events)
    warnings.extend(date_warnings)

    detected, w = _parse_utc(item.get("dateDetected") or item.get("detectedAt"))
    if w: warnings.append("invalid_dateDetected")
    if detected is None:
        event_detected = []
        for event in events:
            for key in ("dateDetected", "detectedAt"):
                parsed, ew = _parse_utc(event.get(key))
                if ew: warnings.append(f"invalid_event_{key}")
                if parsed is not None: event_detected.append(parsed)
        if event_detected: detected = min(event_detected)

    first_seen, w = _parse_utc(item.get("dateFirstSeen"))
    if w: warnings.append("invalid_dateFirstSeen")
    last_seen, w = _parse_utc(item.get("dateLastSeen"))
    if w: warnings.append("invalid_dateLastSeen")

    source_types = _strings(item.get("sourceType"))
    source_objects = _objects(item.get("source"))
    source_ids = _unique([_text(s.get("id")) for s in source_objects])
    source_links = _unique([_valid_url(s.get("url")) or _valid_url(s.get("link")) or _valid_url(s.get("href")) or _text(s.get("id")) for s in source_objects])
    source_names = _unique([_text(s.get("name")) or _text(s.get("type")) for s in source_objects])
    event_source_names = _unique([_text(_object(e.get("source")).get("name")) or _text(_object(e.get("source")).get("type")) for e in events])
    if event_source_names: source_names = event_source_names

    malware_objects = _objects(item.get("malware"))
    event_malware = tuple(_object(e.get("malware")) for e in events if isinstance(e.get("malware"), dict))
    stealer_families = _unique([_text(m.get("name")) for m in (*malware_objects, *event_malware)])
    malware_ids = _unique([_text(m.get("id")) for m in (*malware_objects, *event_malware)])

    clients = [_object(_object(e.get("client")).get("ipv4")) for e in events]
    victim_ips = _unique([_parse_ip(c.get("ip")) for c in clients])
    victim_countries = _unique([_text(c.get("countryName")) for c in clients])
    victim_cities = _unique([_text(c.get("city")) for c in clients])
    victim_providers = _unique([_text(c.get("provider")) for c in clients])
    target_urls = _unique([_valid_url(_object(e.get("cnc")).get("url")) for e in events])
    threat_actors = tuple(dict.fromkeys((*_strings(item.get("threatActor")), *_unique([_text(e.get("threatActor")) for e in events]))))
    event_ids = _unique([_text(e.get("id")) for e in events])

    identity = f"provider:{provider_record_id}" if provider_record_id else _fallback_identity(
        account=account, domain=domain, first_seen=first_seen, last_seen=last_seen,
        source_types=source_types, event_ids=event_ids)

    raw_event_count = item.get("eventCount")
    event_count = raw_event_count if isinstance(raw_event_count, int) and not isinstance(raw_event_count, bool) else len(events)
    if raw_event_count is not None and not isinstance(raw_event_count, int): warnings.append("invalid_eventCount")

    service_domain = _text(service.get("domain"))
    service_host = _text(service.get("host"))
    service_url = _valid_url(service.get("url"))
    if service.get("url") is not None and service_url is None: warnings.append("invalid_service_url")

    fingerprint_material = {
        "provider": provider, "compromise_identity": identity, "account": account, "domain": domain,
        "compromised_date": compromised_date.isoformat() if compromised_date else None,
        "last_compromised_date": last_compromised_date.isoformat() if last_compromised_date else None,
        "date_detected": detected.isoformat() if detected else None,
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "event_count": event_count, "event_ids": event_ids,
        "stealer_families": stealer_families, "malware_ids": malware_ids,
        "victim_ips": victim_ips, "victim_countries": victim_countries, "victim_cities": victim_cities,
        "victim_providers": victim_providers, "target_urls": target_urls, "source_types": source_types,
        "source_ids": source_ids, "source_names": source_names, "source_links": source_links,
        "threat_actors": threat_actors, "service_domain": service_domain, "service_host": service_host,
        "service_url": service_url, "login_url": service_url, "credential_present": password is not None,
    }
    fingerprint = "sha256:" + hashlib.sha256(json.dumps(fingerprint_material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    return CanonicalIntelligenceRecord(
        provider=provider, provider_record_id=provider_record_id, compromise_identity=identity,
        account=account, username=account, password=password, victim_domain=domain,
        compromised_date=compromised_date, last_compromised_date=last_compromised_date,
        date_detected=detected, first_seen=first_seen, last_seen=last_seen, event_count=event_count,
        stealer_families=stealer_families, malware_ids=malware_ids, victim_ips=victim_ips,
        victim_countries=victim_countries, victim_cities=victim_cities, victim_providers=victim_providers,
        target_urls=target_urls, source_types=source_types, source_ids=source_ids, source_names=source_names,
        source_links=source_links, threat_actors=threat_actors, service_domain=service_domain,
        service_host=service_host, service_url=service_url, login_url=service_url, event_ids=event_ids,
        credential_present=password is not None, observation_fingerprint=fingerprint,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def normalize_records(items: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...], *, provider: str = "groupib") -> tuple[CanonicalIntelligenceRecord, ...]:
    records = [normalize_record(item, provider=provider) for item in items]
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    return tuple(sorted(records, key=lambda r: (-(r.last_seen or r.first_seen or minimum).timestamp(), r.compromise_identity)))
