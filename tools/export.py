"""Export only allowlisted performance measurements for public GitHub benchmarks."""

import argparse
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path


FIELDS = (
    "source_archives", "indexed_archives", "total_media", "confirmed", "resumed",
    "failed", "unknown", "workers", "staging_bytes", "source_bytes", "total_media_bytes",
    "confirmed_bytes", "network_in_bytes", "network_out_bytes", "network_bytes",
    "elapsed_seconds", "instance_elapsed_seconds", "compute_estimate_microusd",
    "monthly_price_microusd", "transfer_limit_bytes", "bundle_transfer_gb",
)
STATES = {"starting", "running", "complete", "stopped", "unavailable"}


def public_sample(value):
    stamp = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None or value["state"] not in STATES:
        raise ValueError("Invalid benchmark observation")
    row = {"observed_at": stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
           "state": value["state"]}
    for field in FIELDS:
        item = value.get(field)
        if item is not None and (type(item) is not int or not 0 <= item <= 2**53 - 1):
            raise ValueError("Invalid numeric benchmark measurement")
        row[field] = item
    return row


def export(source, directory):
    rows = {}
    with source.open() as stream:
        for line in stream:
            if not line.endswith("\n"):
                break
            value = public_sample(json.loads(line))
            rows[value["observed_at"]] = value
    samples = [rows[key] for key in sorted(rows)]
    if not samples:
        raise ValueError("No complete measurements to publish")
    first, last = samples[0], samples[-1]
    seconds = (datetime.fromisoformat(last["observed_at"].replace("Z", "+00:00")) -
               datetime.fromisoformat(first["observed_at"].replace("Z", "+00:00"))).total_seconds()
    summary = dict(status="in_progress" if last["state"] != "complete" else "complete",
                   latest_state=last["state"], observations=len(samples),
                   first_observed_at=first["observed_at"], last_observed_at=last["observed_at"],
                   measurement_window_seconds=seconds,
                   measurements={key: last[key] for key in FIELDS if last[key] is not None},
                   quota_treatment="unverified", cost_basis="approximate server compute; not billed cost")
    for name in ("network_in_bytes", "network_out_bytes"):
        if seconds > 0 and first[name] is not None and last[name] is not None and last[name] >= first[name]:
            summary[name.replace("_bytes", "_average_MBps")] = (last[name] - first[name]) / seconds / 1e6
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=("observed_at", "state", *FIELDS), lineterminator="\n")
    writer.writeheader()
    writer.writerows(samples)
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in (("samples.csv", output.getvalue()), ("summary.json", json.dumps(summary, indent=2) + "\n")):
        temporary = directory / (name + ".tmp")
        temporary.write_text(text)
        temporary.replace(directory / name)
    return len(samples)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print("Exported measurement rows:", export(args.source, args.directory))
