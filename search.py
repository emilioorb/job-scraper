"""Busca ofertas en LinkedIn, Indeed y Google con JobSpy y las guarda en un CSV sin duplicados.

Los valores salen de la sección [search] del perfil; cualquier flag de la línea de comandos los sobrescribe.
"""

import argparse
import csv
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from jobspy import scrape_jobs

from config import DEFAULT_PROFILE, load_profile

OUTPUT_COLUMNS = [
    "site", "title", "company", "location", "is_remote", "job_type",
    "date_posted", "min_amount", "max_amount", "currency", "job_url",
]
RESULTS_DIR = Path(__file__).parent / "results"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE, help="Perfil TOML (default: profile.toml)")
    parser.add_argument("--terms", nargs="+")
    parser.add_argument("--location")
    parser.add_argument("--country", help="País para Indeed (ej. 'mexico', 'colombia', 'usa')")
    parser.add_argument("--sites", nargs="+")
    parser.add_argument("--remote", action="store_true", default=None, help="Solo ofertas remotas")
    parser.add_argument("--hours", type=int, help="Antigüedad máxima en horas")
    parser.add_argument("--results", type=int, help="Resultados por sitio y término")
    return parser.parse_args()


def resolve_settings(args: argparse.Namespace) -> argparse.Namespace:
    settings = asdict(load_profile(args.profile).search)
    overrides = {key: value for key, value in vars(args).items() if value is not None and key in settings}
    return argparse.Namespace(**{**settings, **overrides})


def search_term(term: str, args: argparse.Namespace) -> pd.DataFrame:
    return scrape_jobs(
        site_name=args.sites,
        search_term=term,
        google_search_term=f"{term} jobs {args.location} since yesterday",
        location=args.location,
        country_indeed=args.country,
        is_remote=args.remote,
        hours_old=args.hours,
        results_wanted=args.results,
        verbose=0,
    )


def main() -> None:
    args = resolve_settings(parse_args())
    if not args.terms:
        raise SystemExit("Define [search].terms en el perfil o pasa --terms.")
    frames = []
    for term in args.terms:
        try:
            frames.append(search_term(term, args).assign(search_term=term))
            print(f"✓ {term}: {len(frames[-1])} ofertas")
        except Exception as error:  # una bolsa caída no debe detener las demás búsquedas
            print(f"✗ {term}: {error}")

    if not frames:
        print("Sin resultados.")
        return

    jobs = pd.concat(frames, ignore_index=True).drop_duplicates(subset="job_url")
    columns = [c for c in OUTPUT_COLUMNS if c in jobs.columns] + ["search_term"]
    RESULTS_DIR.mkdir(exist_ok=True)
    output = RESULTS_DIR / f"jobs_{datetime.now():%Y-%m-%d_%H%M}.csv"
    jobs[columns].to_csv(output, index=False, quoting=csv.QUOTE_NONNUMERIC)
    print(f"\n{len(jobs)} ofertas únicas → {output}")


if __name__ == "__main__":
    main()
