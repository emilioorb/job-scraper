"""Busca ofertas en bolsas remotas, bolsas locales de LatAm, Wellfound, HN y páginas ATS de empresas.

Qué buscar, dónde y qué descartar se define en el perfil TOML (ver profiles/).
"""

import argparse
import csv
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import DEFAULT_PROFILE, BoardSettings, Profile, load_profile

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept-Language": "es-CR,es;q=0.9,en;q=0.8",
}
RESULTS_DIR = Path(__file__).parent / "results"
MAX_AGE_DAYS = {"hn": 35, "wellfound": 30, "greenhouse": 30, "lever": 30, "ashby": 30}
LOCAL_SOURCES = {"getonbrd", "computrabajo", "elempleo"}
SPANISH_MONTHS = {m: i for i, m in enumerate(
    ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"], start=1)}


@dataclass(frozen=True)
class Job:
    source: str
    title: str
    company: str
    location: str
    date_posted: str
    url: str
    details: str


def build_session() -> requests.Session:
    retry = Retry(total=4, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET", "POST"])
    session = requests.Session()
    session.headers.update(HEADERS)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


SESSION = build_session()


def get(url: str, **params: str) -> requests.Response:
    response = SESSION.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response


def iso_from_timestamp(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%d")


def days_ago(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def remotive(_: BoardSettings) -> Iterator[Job]:
    """La API pública ignora el filtro por categoría y solo expone las ofertas más recientes."""
    for j in get("https://remotive.com/api/remote-jobs").json()["jobs"]:
        yield Job("remotive", j["title"], j["company_name"], j["candidate_required_location"],
                  j["publication_date"][:10], j["url"], ", ".join([j.get("category", ""), *j.get("tags", [])]))


def remoteok(_: BoardSettings) -> Iterator[Job]:
    for j in get("https://remoteok.com/api").json()[1:]:
        yield Job("remoteok", j["position"], j["company"], j.get("location") or "", j["date"][:10], j["url"],
                  ", ".join(j.get("tags", [])))


def himalayas(_: BoardSettings) -> Iterator[Job]:
    for offset in range(0, 400, 20):
        for j in get("https://himalayas.app/jobs/api", limit="20", offset=str(offset)).json()["jobs"]:
            location = ", ".join(j.get("locationRestrictions") or ["Worldwide"])
            yield Job("himalayas", j["title"], j["companyName"], location, iso_from_timestamp(j["pubDate"]),
                      j["applicationLink"], ", ".join(j.get("categories", [])))


def getonbrd(settings: BoardSettings) -> Iterator[Job]:
    for query in settings.getonbrd_queries:
        data = get("https://www.getonbrd.com/api/v0/search/jobs", query=query, per_page="50").json()["data"]
        for j in data:
            a = j["attributes"]
            if a.get("remote"):
                yield Job("getonbrd", a["title"], "", a.get("remote_modality", "remote"),
                          iso_from_timestamp(a["published_at"]), j["links"]["public_url"], "")


def computrabajo_date(block: str) -> str:
    if "Ayer" in block:
        return days_ago(1)
    if match := re.search(r"Hace\s+(\d+)\s+d", block):
        return days_ago(int(match.group(1)))
    if "más de 30" in block:
        return days_ago(31)
    return days_ago(0)


def computrabajo(settings: BoardSettings) -> Iterator[Job]:
    site = f"https://{settings.computrabajo_country}.computrabajo.com"
    for query in settings.computrabajo_queries:
        page = get(f"{site}/trabajo-de-{query.replace(' ', '-')}").text
        for block in page.split("data-offers-grid-offer-item-container")[1:]:
            link = re.search(r'class="js-o-link[^"]*" href="([^"#]+)[^"]*">\s*([^<]+)', block)
            if not link:
                continue
            company = re.search(r"offer-grid-article-company-url>\s*([^<]+)", block)
            location = re.search(r'<span class="mr10">\s*([^<]+)', block)
            yield Job("computrabajo", clean(link.group(2)), clean(company.group(1)) if company else "",
                      clean(location.group(1)) if location else settings.computrabajo_country.upper(),
                      computrabajo_date(block), f"{site}{link.group(1)}", "")


def elempleo_date(block: str) -> str:
    match = re.search(r"Publicado\s+(\d{1,2})\s+(\w{3})\w*\s+(\d{4})", block)
    if not match or match.group(2).lower() not in SPANISH_MONTHS:
        return days_ago(0)
    day, month, year = match.groups()
    return date(int(year), SPANISH_MONTHS[month.lower()], int(day)).isoformat()


def elempleo(settings: BoardSettings) -> Iterator[Job]:
    """El buscador por palabra clave requiere sesión; se filtran las 50 ofertas más recientes."""
    page = get(f"https://www.elempleo.com/{settings.elempleo_country}/ofertas-empleo/").text
    for block in page.split('result-item">')[1:]:
        title = re.search(r'js-offer-title" href="([^"?]+)[^"]*" title="([^"]+)"', block)
        if not title:
            continue
        company = re.search(r'js-offer-company">\s*([^<]+)', block)
        city = re.search(r'js-offer-city">\s*([^<]+)', block)
        yield Job("elempleo", clean(title.group(2)), clean(company.group(1)) if company else "",
                  clean(city.group(1)) if city else settings.elempleo_country.upper(), elempleo_date(block),
                  f"https://www.elempleo.com{title.group(1)}", "")


def wellfound(settings: BoardSettings) -> Iterator[Job]:
    for role in settings.wellfound_roles:
        page = get(f"https://wellfound.com/role/r/{role}").text
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        if not match:
            continue
        state: dict[str, dict[str, object]] = json.loads(match.group(1))[
            "props"]["pageProps"]["apolloState"]["data"]
        company_by_job = {
            ref["__ref"]: str(node.get("name", ""))
            for node in state.values() if node.get("__typename") == "StartupResult"
            for ref in node.get("highlightedJobListings", [])  # type: ignore[union-attr]
        }
        for key, j in state.items():
            if j.get("__typename") != "JobListingSearchResult":
                continue
            accepted = ", ".join(j.get("acceptedRemoteLocationNames") or [])  # type: ignore[arg-type]
            details = f"{j.get('compensation') or ''} | min {j.get('yearsExperienceMin') or '?'} años"
            yield Job("wellfound", str(j["title"]), company_by_job.get(key, ""), accepted,
                      iso_from_timestamp(float(j["liveStartAt"])),  # type: ignore[arg-type]
                      f"https://wellfound.com/jobs/{j['id']}-{j['slug']}", details)


def hacker_news(_: BoardSettings) -> Iterator[Job]:
    """El hilo mensual 'Who is hiring' no tiene campos: la primera línea del comentario suele incluir la ubicación."""
    hits = get("https://hn.algolia.com/api/v1/search_by_date", tags="story,author_whoishiring", hitsPerPage="5").json()["hits"]
    thread = next(h for h in hits if h["title"].startswith("Ask HN: Who is hiring"))
    for comment in get(f"https://hn.algolia.com/api/v1/items/{thread['objectID']}").json()["children"]:
        text = comment.get("text") or ""
        if "remote" not in text.lower():
            continue
        header = clean(text.split("<p>")[0])
        company = header.split("|")[0].strip()
        yield Job("hn", header[:160], company, header, comment["created_at"][:10],
                  f"https://news.ycombinator.com/item?id={comment['id']}", clean(text)[:500])


def greenhouse(company: str) -> Iterator[Job]:
    for j in get(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs").json()["jobs"]:
        location = j.get("location", {}).get("name", "")
        yield Job("greenhouse", j["title"], company, location, j["updated_at"][:10], j["absolute_url"], "")


def lever(company: str) -> Iterator[Job]:
    for j in get(f"https://api.lever.co/v0/postings/{company}", mode="json").json():
        location = ", ".join(j.get("categories", {}).get("allLocations") or [j.get("categories", {}).get("location", "")])
        yield Job("lever", j["text"], company, location, iso_from_timestamp(j["createdAt"] / 1000), j["hostedUrl"], "")


def ashby(company: str) -> Iterator[Job]:
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{company}").json()["jobs"]:
        secondary = [s.get("location", "") for s in j.get("secondaryLocations") or []]
        location = ", ".join([j.get("location", ""), *secondary])
        yield Job("ashby", j["title"], company, location, j["publishedAt"][:10], j["jobUrl"], "")


ATS_FETCHERS: dict[str, Callable[[str], Iterator[Job]]] = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}


def company_ats(settings: BoardSettings) -> Iterator[Job]:
    tasks = [(ATS_FETCHERS[ats], company) for ats, companies in settings.ats.items() for company in companies]

    def safe(task: tuple[Callable[[str], Iterator[Job]], str]) -> list[Job]:
        fetch, company = task
        try:
            return list(fetch(company))
        except requests.RequestException:
            return []

    with ThreadPoolExecutor(12) as pool:
        for jobs in pool.map(safe, tasks):
            yield from jobs


SOURCES: dict[str, Callable[[BoardSettings], Iterable[Job]]] = {
    "remotive": remotive, "remoteok": remoteok, "himalayas": himalayas, "getonbrd": getonbrd,
    "computrabajo": computrabajo, "elempleo": elempleo, "wellfound": wellfound, "hn": hacker_news,
    "ats": company_ats,
}


def is_relevant(job: Job, profile: Profile) -> bool:
    filters = profile.filters
    max_age = timedelta(days=MAX_AGE_DAYS.get(job.source, filters.max_age_days))
    recent = date.today() - date.fromisoformat(job.date_posted[:10]) <= max_age
    location_ok = job.source in LOCAL_SOURCES or filters.accepts_location(job.location)
    return (recent and location_ok and filters.wants(f"{job.title} {job.details}")
            and not filters.rejects(job.title))


def previously_seen_urls() -> set[str]:
    seen: set[str] = set()
    for path in RESULTS_DIR.glob("*.csv"):
        with path.open(encoding="utf-8") as file:
            seen.update(row.get("url") or row.get("job_url") or "" for row in csv.DictReader(file))
    return seen


def fetch_source(name: str, profile: Profile) -> tuple[str, list[Job], str]:
    try:
        return name, [j for j in SOURCES[name](profile.boards) if is_relevant(j, profile)], ""
    except Exception as error:  # una bolsa caída no debe detener las demás
        return name, [], str(error)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Perfil TOML (default: profile.toml)")
    parser.add_argument("--sources", nargs="+", choices=SOURCES, help="Sobrescribe las fuentes del perfil")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profile = load_profile(args.profile)
    sources = args.sources or profile.boards.sources
    unknown = set(sources) - SOURCES.keys()
    if not sources:
        raise SystemExit("El perfil no tiene fuentes en [boards].sources.")
    if unknown:
        raise SystemExit(f"Fuentes desconocidas en el perfil: {', '.join(sorted(unknown))}. Válidas: {', '.join(SOURCES)}")

    print(f"Perfil: {profile.name}\n")
    seen = previously_seen_urls()
    jobs: dict[str, Job] = {}
    with ThreadPoolExecutor(len(sources)) as pool:
        for name, found, error in pool.map(lambda name: fetch_source(name, profile), sources):
            print(f"✗ {name}: {error}" if error else f"✓ {name}: {len(found)} relevantes")
            jobs.update({j.url: j for j in found})

    ranked = sorted(jobs.values(), key=lambda j: j.date_posted, reverse=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    output = RESULTS_DIR / f"boards_{datetime.now():%Y-%m-%d_%H%M}.csv"
    columns = [f.name for f in fields(Job)] + ["is_new"]
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows({**asdict(j), "is_new": j.url not in seen} for j in ranked)
    new_count = sum(j.url not in seen for j in ranked)
    print(f"\n{len(ranked)} ofertas ({new_count} nuevas) → {output}")


if __name__ == "__main__":
    main()
