"""News-driven incident automation.

Polls keyless news sources (Google News RSS, GDELT) for landslide events
published within the last N hours, resolves the nearest known district/village
Geo location, and auto-creates incidents (with priority + alert + audit log).
Duplicates are de-duplicated via a persistent URL tracker in SystemConfig, so
the same article is only ingested once regardless of how often the monitor runs.
"""
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.geo import District, State, Village
from app.models.risk import Alert, EmergencyResponse, Incident, SystemConfig
from app.services.audit_service import audit
from app.services.prediction_service import create_alert
from app.services.priority_service import compute_priority

SEEN_KEY = "news_seen_urls"
_DOMAIN_HINTS = {"thehindu", "indianexpress", "timesofindia", "hindustantimes",
                 "ndtv", "theprint", "deccanherald", "eastmojo", "northeastnow",
                 "telegraphindia", "assamtribune", "sentinelassam", "morungexpress",
                 "nagalandpost", "thesangaiexpress", "easternmirror", "ifsbut"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower().strip())


def _norm_headline(desc: str) -> str:
    headline = _strip_html(desc).split(" — ")[0].split(" – ")[0]
    return _norm(headline)


RELEVANT_KEYWORDS = ("landslide", "landslip", " land slide", "mudslide",
                     "slope failure", "hill slope", "rockfall", "rock fall",
                     "soil erosion", "land caving")
HIGH_SEVERITY = ("death", "dead", "died", "injured", "injur", "hospital",
                 "rescue", "evacuat", "collapsed", "buried", "missing",
                 "casualt", "critical", "severe", "massive", "destroyed",
                 "damaged")


def _classify(text: str) -> tuple[str, str]:
    t = _norm(text)
    if any(k in t for k in ("rockfall", "rock fall", "boulder", "stone")):
        itype = "rockfall"
    elif "crack" in t or "fissure" in t:
        itype = "slope_crack"
    elif "flood" in t or "inundat" in t:
        itype = "flooding"
    elif "road" in t and any(k in t for k in ("block", "closed", "cut", "break")):
        itype = "blocked_road"
    else:
        itype = "slope_movement"
    severity = "high" if any(k in t for k in HIGH_SEVERITY) else "medium"
    return itype, severity


def _strip_html(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _is_relevant(text: str) -> bool:
    t = _norm(text)
    return any(k in t for k in RELEVANT_KEYWORDS)


def _is_northeast(text: str) -> bool:
    t = _norm(text)
    states = ("assam", "meghalaya", "mizoram", "tripura", "nagaland", "manipur",
              "arunachal", "sikkim", "northeast", "north east", "indian")
    return any(s in t for s in states)


def _fetch_google_rss() -> list[dict]:
    days = max(1, round(settings.NEWS_TIMESPAN_HOURS / 24))
    url = "https://news.google.com/rss/search"
    params = {"q": f"({settings.NEWS_QUERY}) when:{days}d",
              "hl": "en-IN", "gl": "IN", "ceid": "IN:en"}
    resp = httpx.get(url, params=params, timeout=20, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 (compatible; LandslideMonitor/1.0)"})
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    items = []
    for item in root.iter("item"):
        def _text(tag: str) -> str:
            el = item.find(tag)
            return (el.text or "").strip() if el is not None else ""
        pub = _text("pubDate")
        try:
            published = parsedate_to_datetime(pub).astimezone(timezone.utc)
        except (TypeError, ValueError):
            published = _now()
        items.append({
            "title": _text("title"),
            "url": _text("link"),
            "description": _text("description"),
            "domain": (_text("source") or "google-news"),
            "published": published,
        })
    return items


def _fetch_gdelt() -> list[dict]:
    now = _now()
    start = now - timedelta(hours=settings.NEWS_TIMESPAN_HOURS)
    resp = httpx.get(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query": settings.NEWS_QUERY,
            "mode": "artlist",
            "maxrecords": settings.NEWS_MAX_RECORDS,
            "format": "json",
            "sort": "datedesc",
            "startdatetime": start.strftime("%Y%m%d%H%M%S"),
            "enddatetime": now.strftime("%Y%m%d%H%M%S"),
        },
        timeout=25,
    )
    resp.raise_for_status()
    out = []
    for row in resp.json().get("articles", []):
        try:
            published = datetime.strptime(row.get("seendate", ""), "%Y%m%d%H%M%S") \
                .replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            published = _now()
        out.append({
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "description": row.get("title", ""),
            "domain": row.get("domain", "gdelt"),
            "published": published,
        })
    return out


def _fetch_news() -> list[dict]:
    provider = settings.NEWS_PROVIDER
    if provider == "mock" or not settings.NEWS_ENABLED:
        return []
    attempts = ["google_rss", "gdelt"] if provider == "auto" else [provider]
    for p in attempts:
        try:
            if p == "google_rss":
                items = _fetch_google_rss()
            else:
                items = _fetch_gdelt()
            if items:
                return items
        except Exception as exc:  # pragma: no cover - upstream dependency
            print(f"news provider {p} failed: {exc}")
    return []


def _read_seen(db: Session) -> dict[str, str]:
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == SEEN_KEY))
    if not row:
        return {}
    try:
        data = json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {str(e.get("url")): str(e.get("at")) for e in data if e.get("url")}


def _mark_seen(db: Session, url: str) -> None:
    seen = _read_seen(db)
    seen[url] = _now().isoformat()
    pruned = {}
    for u, at in seen.items():
        try:
            age = _now() - datetime.fromisoformat(at).astimezone(timezone.utc)
        except (ValueError, TypeError):
            age = _now() - _now()
        if age < timedelta(days=30):
            pruned[u] = at
    entries = [{"url": u, "at": at} for u, at in pruned.items()]
    row = db.scalar(select(SystemConfig).where(SystemConfig.key == SEEN_KEY))
    if row is None:
        row = SystemConfig(key=SEEN_KEY, value=json.dumps(entries), description="Seen news URLs (auto-incident dedupe)")
        db.add(row)
    else:
        row.value = json.dumps(entries)
    db.commit()


def _resolve_location(db: Session, text: str) -> dict | None:
    """Match known NE districts/villages/states to the news text."""
    t = _norm(text)
    best = None  # (specificity, dict)
    for v in db.scalars(select(Village)).all():
        if v.name and _norm(v.name) in t:
            best = (2, {"district_id": v.district_id, "latitude": v.latitude,
                        "longitude": v.longitude, "place": v.name})
            break
    if best is None:
        for d in db.scalars(select(District)).all():
            if d.name and _norm(d.name) in t:
                best = (1, {"district_id": d.id, "latitude": d.latitude,
                            "longitude": d.longitude, "place": d.name})
                break
    if best is None:
        for st in db.scalars(select(State)).all():
            if st.name and _norm(st.name) in t:
                capital = db.scalar(
                    select(District).where(District.state_id == st.id)
                    .order_by(District.population.desc()).limit(1)
                )
                if capital:
                    best = (0, {"district_id": capital.id, "latitude": capital.latitude,
                                "longitude": capital.longitude, "place": capital.name})
                break
    return best[1] if best else None


def diagnose_news(db: Session) -> dict:
    """Dry-run news pipeline diagnostics (no DB writes)."""
    errors = []
    fetched = []
    provider = settings.NEWS_PROVIDER
    attempts = ["google_rss", "gdelt"] if provider == "auto" else [provider]
    for p in attempts:
        try:
            fetched = _fetch_google_rss() if p == "google_rss" else _fetch_gdelt()
            if fetched:
                provider = p
                break
        except Exception as exc:
            errors.append(f"{p}: {exc}")
    relevant = [x for x in fetched if _is_relevant(f"{x.get('title')} {x.get('description')}")]
    ne = [x for x in relevant if _is_northeast(f"{x.get('title')} {x.get('description')}")]
    resolved = 0
    for x in ne:
        if _resolve_location(db, f"{x.get('title')} {x.get('description')}"):
            resolved += 1
    return {
        "enabled": settings.NEWS_ENABLED,
        "configured_provider": provider if fetched else attempts[0],
        "fetched": len(fetched),
        "relevant": len(relevant),
        "northeast": len(ne),
        "geo_resolved": resolved,
        "errors": errors,
        "sample": [{"title": x.get("title"), "domain": x.get("domain"),
                    "published": str(x.get("published"))} for x in ne[:5]],
    }


def process_news_incidents(db: Session) -> int:
    """Fetch recent news, auto-create new incidents once per article URL."""
    if not settings.NEWS_ENABLED:
        return 0
    seen = _read_seen(db)
    cutoff = _now() - timedelta(hours=settings.NEWS_TIMESPAN_HOURS)
    created = 0
    for item in _fetch_news():
        if not item.get("url") or item["url"] in seen:
            continue
        published = item.get("published", _now())
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        if published < cutoff:
            continue
        text = f"{item.get('title')} {item.get('description')}"
        if not _is_relevant(text):
            continue
        if not _is_northeast(text):
            continue
        loc = _resolve_location(db, text)
        itype, severity = _classify(text)
        title_s = _strip_html(item.get("title"))
        desc_s = _strip_html(item.get("description"))
        if desc_s.lower().startswith(title_s.lower()):
            desc_s = desc_s[len(title_s):].strip(" ,.–—")
        desc = f"{title_s} — {desc_s}".strip(" —")
        dup = next((d for d in db.scalars(select(Incident).where(
            Incident.source == "auto_news",
            Incident.reported_at >= _now() - timedelta(days=30))).all()
            if _norm_headline(d.description) == _norm_headline(desc)), None)
        if dup:
            _mark_seen(db, item["url"])
            continue
        inc = Incident(
            incident_type=itype,
            status="reported",
            severity=severity,
            verification_status="pending",
            description=desc,
            latitude=loc["latitude"] if loc else None,
            longitude=loc["longitude"] if loc else None,
            district_id=loc["district_id"] if loc else None,
            reported_by=None,
            source="auto_news",
            source_url=item.get("url"),
        )
        db.add(inc)
        db.flush()
        prio = compute_priority(inc, db)
        db.add(EmergencyResponse(
            incident_id=inc.id,
            priority_score=prio["priority_score"],
            priority_class=prio["priority_class"],
            population_affected=0,
        ))
        audit(db, "incident.create", "incident", inc.id,
              f"Auto-created {itype} incident from news ({item.get('domain', 'news')})", None)
        raise_news_alert(db, inc, loc, title=item.get("title"), domain=item.get("domain"))
        db.commit()
        _mark_seen(db, item["url"])
        created += 1
    return created


def raise_news_alert(db: Session, inc: Incident, loc: dict | None, *, title: str, domain: str) -> Alert:
    alert_sev = "warning" if inc.severity == "high" else "watch"
    risk_level = "HIGH" if inc.severity == "high" else "MODERATE"
    place = f" in {loc['place']}" if loc else ""
    return create_alert(
        db,
        title=f"News report: {title or inc.incident_type}",
        message=f"Auto-detected from {domain or 'news'}{place}. "
                f"{inc.description or ''}".strip(),
        severity=alert_sev,
        alert_type="news_report",
        risk_level=risk_level,
        cause="News article (auto-detected)",
        recommended_action="Review and dispatch assessment team",
        district_id=inc.district_id,
        lat=inc.latitude,
        lon=inc.longitude,
    )