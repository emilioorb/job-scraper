"""Carga el perfil de búsqueda (TOML) que define qué ofertas interesan y dónde buscarlas."""

import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PROFILE = Path(__file__).parent / "profile.toml"
EXAMPLES_DIR = Path(__file__).parent / "profiles"


def keyword_regex(keyword: str) -> str:
    """Palabra completa por defecto; un '*' final la convierte en prefijo ('contad*' → contador, contadora)."""
    if keyword.endswith("*"):
        return rf"(?<!\w){re.escape(keyword[:-1])}"
    return rf"(?<!\w){re.escape(keyword)}(?!\w)"


def keyword_pattern(keywords: list[str]) -> re.Pattern[str] | None:
    cleaned = [k.strip() for k in keywords if k.strip()]
    if not cleaned:
        return None
    return re.compile("|".join(keyword_regex(k) for k in cleaned), re.I)


@dataclass(frozen=True)
class Filters:
    include: re.Pattern[str] | None
    exclude: re.Pattern[str] | None
    locations: re.Pattern[str] | None
    max_age_days: int

    def wants(self, text: str) -> bool:
        return self.include is None or bool(self.include.search(text))

    def rejects(self, text: str) -> bool:
        return self.exclude is not None and bool(self.exclude.search(text))

    def accepts_location(self, location: str) -> bool:
        return self.locations is None or bool(self.locations.search(location))


@dataclass(frozen=True)
class SearchSettings:
    terms: list[str]
    location: str = "Costa Rica"
    country: str = "costa rica"
    sites: list[str] = field(default_factory=lambda: ["linkedin", "indeed", "google"])
    remote: bool = False
    hours: int = 72
    results: int = 20


@dataclass(frozen=True)
class BoardSettings:
    sources: list[str]
    getonbrd_queries: list[str] = field(default_factory=list)
    computrabajo_country: str = "cr"
    computrabajo_queries: list[str] = field(default_factory=list)
    elempleo_country: str = "cr"
    wellfound_roles: list[str] = field(default_factory=list)
    ats: dict[str, list[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Profile:
    name: str
    filters: Filters
    search: SearchSettings
    boards: BoardSettings


def load_profile(path: Path = DEFAULT_PROFILE) -> Profile:
    if not path.exists():
        examples = ", ".join(p.name for p in sorted(EXAMPLES_DIR.glob("*.toml")))
        sys.exit(f"No existe el perfil '{path}'. Copia uno de profiles/ ({examples}) como profile.toml "
                 "o pasa --profile <ruta>.")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    filters = data.get("filters", {})
    return Profile(
        name=data.get("profile", {}).get("name", path.stem),
        filters=Filters(
            include=keyword_pattern(filters.get("include", [])),
            exclude=keyword_pattern(filters.get("exclude", [])),
            locations=keyword_pattern(filters.get("locations", [])),
            max_age_days=filters.get("max_age_days", 10),
        ),
        search=SearchSettings(**data.get("search", {"terms": []})),
        boards=BoardSettings(**data.get("boards", {"sources": []})),
    )
