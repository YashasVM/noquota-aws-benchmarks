"""Refresh anonymous measurements from the authenticated tracker history."""

from datetime import datetime
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from export import export, public_sample


BASE = "https://a.yash0.in/noquota-live/api/"
JOB = re.compile(r"[0-9a-f]{64}", re.IGNORECASE)
UTC = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        raise ValueError("Tracker redirects are not allowed")


def get_json(key, path):
    request = Request(BASE + path, headers={
        "Authorization": "Bearer " + key,
        "User-Agent": "noquota-benchmark-publisher/0.1",
        "Accept": "application/json",
    })
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        data = response.read(2 * 1024**2 + 1)
        if len(data) > 2 * 1024**2:
            raise ValueError("Tracker response is too large")
        return json.loads(data)


def timestamp(value):
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise ValueError("Invalid observation time")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def download_samples(key):
    if not isinstance(key, str) or not key.strip() or "\r" in key or "\n" in key:
        raise ValueError("Missing or invalid view key")
    current = get_json(key, "snapshot")["current"]
    job = current["job_id"]
    if not isinstance(job, str) or not JOB.fullmatch(job):
        raise ValueError("Invalid tracker job")
    timestamp(current["observed_at"])
    samples, before = [], None
    # shortcut: cap each refresh at 100,000 observations; raise if runs exceed 139 days at 120s.
    for _ in range(200):
        query = {"job_id": job, "limit": 500}
        if before is not None:
            query["before"] = before
        page = get_json(key, "history?" + urlencode(query))
        rows = page.get("samples")
        if (page.get("job_id") != job or type(page.get("has_more")) is not bool
                or not isinstance(rows, list) or not 0 < len(rows) <= 500):
            raise ValueError("Invalid tracker history page")
        previous = None
        for row in rows:
            if row.get("job_id") != job:
                raise ValueError("History crossed jobs")
            observed = timestamp(row["observed_at"])
            if ((previous is not None and observed <= previous)
                    or (before is not None and observed >= timestamp(before))):
                raise ValueError("Invalid history order")
            previous = observed
            samples.append(public_sample(row))
        if not page["has_more"]:
            return samples
        next_before = page.get("next_before")
        if timestamp(next_before) != timestamp(rows[0]["observed_at"]):
            raise ValueError("Invalid history cursor")
        before = next_before
    raise ValueError("Tracker history exceeds refresh limit")


def refresh(directory, key):
    samples = download_samples(key)
    # Validate every page before changing either public data file.
    with tempfile.TemporaryDirectory(prefix="noquota-benchmark-") as temporary:
        source = Path(temporary) / "samples.ndjson"
        source.write_text("".join(json.dumps(row) + "\n" for row in samples))
        return export(source, directory)


if __name__ == "__main__":
    try:
        count = refresh(Path(__file__).resolve().parents[1] / "data",
                        os.environ.get("NOQUOTA_VIEW_KEY"))
        print("Published measurement rows:", count)
    except Exception:
        raise SystemExit("Benchmark refresh failed; no data was published.") from None
