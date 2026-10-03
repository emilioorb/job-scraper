"""Descarga el texto de una oferta de empleo para adaptar el CV a ella.

Uso: python describe.py <url-de-la-oferta>
"""

import argparse
import html
import re
from typing import Callable

from boards import clean, get, page_html

NOISE = re.compile(r"<(script|style|nav|header|footer|noscript|svg)\b.*?</\1>", re.S | re.I)


def page_text(url: str) -> str:
    return clean(NOISE.sub(" ", page_html(get(url))))


def linkedin(match: re.Match[str]) -> str:
    """La página normal exige sesión, pero la oferta está en un endpoint público."""
    return page_text(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{match['id']}")


def greenhouse(match: re.Match[str]) -> str:
    job = get(f"https://boards-api.greenhouse.io/v1/boards/{match['company']}/jobs/{match['id']}").json()
    return f"{job['title']}\n\n{clean(html.unescape(job['content']))}"


def lever(match: re.Match[str]) -> str:
    job = get(f"https://api.lever.co/v0/postings/{match['company']}/{match['id']}").json()
    sections = "\n\n".join(f"{s['text']}\n{clean(s['content'])}" for s in job.get("lists", []))
    return f"{job['text']}\n\n{job['descriptionPlain']}\n\n{sections}\n\n{job.get('additionalPlain', '')}"


def ashby(match: re.Match[str]) -> str:
    jobs = get(f"https://api.ashbyhq.com/posting-api/job-board/{match['company']}").json()["jobs"]
    job = next(j for j in jobs if j["id"] == match["id"])
    return f"{job['title']}\n\n{job['descriptionPlain']}"


FETCHERS: list[tuple[re.Pattern[str], Callable[[re.Match[str]], str]]] = [
    (re.compile(r"linkedin\.com/jobs/view/(?:[^/?]*-)?(?P<id>\d+)"), linkedin),
    (re.compile(r"greenhouse\.io/(?P<company>[^/]+)/jobs/(?P<id>\d+)"), greenhouse),
    (re.compile(r"jobs\.lever\.co/(?P<company>[^/]+)/(?P<id>[\w-]+)"), lever),
    (re.compile(r"jobs\.ashbyhq\.com/(?P<company>[^/]+)/(?P<id>[\w-]+)"), ashby),
]


def job_description(url: str) -> str:
    for pattern, fetch in FETCHERS:
        if match := pattern.search(url):
            return fetch(match)
    return page_text(url)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    print(job_description(parser.parse_args().url))


if __name__ == "__main__":
    main()
