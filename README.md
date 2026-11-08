# Noquota AWS import benchmarks

Measured progress, network traffic and approximate compute cost for an ongoing Google Drive Takeout import to Google Photos. This is an early, single-run dataset, not a finished cost-per-TB benchmark.

## Run configuration

| Setting | Value |
| --- | --- |
| Source | 18 Takeout ZIPs, 903,239,751,785 bytes, about 903.24 decimal GB |
| Compute | AWS Lightsail, Sydney, Linux x86_64, 4 GB RAM |
| Included disk | 80 GB; one extracted media file staged at a time |
| Plan | USD 24/month, billed hourly up to the monthly cap |
| Advertised transfer | 2048 GB/month; inbound and outbound both consume the allowance |
| Transfer overage | Sydney outbound overage USD 0.17/GB |
| Import method | Signed-in Drive ZIP range reads, native uploader, one file at a time |
| Native uploader | gotohp-cli v0.11.0, original quality, Pixel XL request profile |
| Sampling | Every 120 seconds once telemetry was attached |
| Source read window | Initially 4 MiB; changed to 16 MiB after bounded A/B testing |
| Runtime libraries | Python 3.12, requests 2.34.2, fsspec 2026.9.0, aiohttp 3.14.5 |

No filenames, Google account identifiers, credential material, server addresses, viewing keys, Drive links or private report rows are published here. Files in `data/` contain only allowlisted numeric measurements, timestamps and a state enum.

## Read the measurements

- [`data/samples.csv`](data/samples.csv) retains every exported observation, in timestamp order.
- [`data/summary.json`](data/summary.json) reports the latest state and averages over the measured window.
- [`METHODOLOGY.md`](METHODOLOGY.md) explains what the counters measure and the limits of projections.
- [`COST_MODEL.md`](COST_MODEL.md) shows a reusable planning calculation.

The import is still running. Read `last_observed_at` and `latest_state` in the summary before interpreting freshness. Data is refreshed periodically, not continuously pushed to GitHub. Initial setup happened before telemetry attachment; missing startup measurements are not fabricated.

## Important limits

A confirmed item can be a fresh upload or an existing remote hash match. Confirmed media bytes therefore differ from bytes actually sent over the network. NIC traffic includes metadata requests, retries, encryption-backup uploads and other host traffic. Report resume avoids re-extracting confirmed entries; it is not partial-file upload resume.

Compute estimates use the plan price divided by 30 days. They are not AWS invoices or observed credit deductions. Taxes, extra services and traffic overages are excluded. The account's effective allowance, credit eligibility and billing-period rules must be checked separately.

Quota-free Google storage treatment has not been independently verified. A Pixel-shaped request and a returned media key do not prove an entitlement. Keep source originals and check account-specific storage treatment before relying on this method.

## Sources

- [AWS Lightsail pricing](https://aws.amazon.com/lightsail/pricing/)
- [AWS regional transfer accounting](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-data-transfer-allowance.html)
- [Lightsail billing](https://aws.amazon.com/lightsail/faq/)
- [gotohp source and authentication methods](https://github.com/xob0t/gotohp)
- [Google Photos backup-quality policy](https://support.google.com/photos/answer/6220791)

## Initial speed investigation

The first workload showed source extraction around 0.25 MB/s while CPU and memory were idle. A bounded, sequential read-only test of the same archive read 16 MiB through fsspec in 13.381 seconds with 4 MiB windows, versus 2.663 seconds with a 16 MiB window. Plain HTTP ranged reads of 16 MiB reached about 6.25 MB/s. The AWS importer now uses 16 MiB windows to reduce request overhead. This is a source-read microbenchmark, not proof of a fivefold whole-run improvement. The repeated-offset tests can benefit from warm provider caches. A subsequent extraction probe crossed its first window at 16 MiB and took 48 seconds overall, so cold reads and range boundaries remain variable.

The restart preserved all confirmed identities and interrupted extraction only after checking that no native upload process was active. The unfinished source file was discarded and re-read. Larger windows can fetch unused bytes near skipped entries; the traffic ceiling remains enabled. Both before and after measurements remain in the dataset.

A further bounded test at separate, previously unread positions read 16 MiB in 5.785 seconds as one request, versus 4.563 seconds using four parallel requests. That smaller gain did not justify enabling four times as many range requests without a whole-job benchmark. No additional instance was provisioned.

## Programmatic updates

The AWS reporter samples every 120 seconds and updates the private dashboard without an LLM. The `Refresh anonymous benchmarks` GitHub Actions workflow runs at minutes 17 and 47 of each hour, or through **Run workflow**. Scheduled runs can be delayed by GitHub; the dataset timestamps show actual freshness.

The repository needs the Actions secret `NOQUOTA_VIEW_KEY`. It is sent only as an HTTPS authorization header to the fixed tracker API. `python3 tools/fetch.py` reads that same environment variable for a manual refresh. No Google credentials, AWS credentials or tracker update key are needed by the publisher.

The fetcher obtains the current job, validates and paginates its complete history, then uses the numeric allowlist exporter. A failed or invalid history response leaves the existing dataset unchanged. The workflow commits only `data/samples.csv` and `data/summary.json` on `automation/measurements` and opens or updates a draft PR. It rejects unexpected staged files and never commits to the default branch or merges. Earlier runs must be archived separately before switching the current dataset to a fresh instance.

Run the publisher checks with `python3 -m unittest discover -s tools -p 'test_*.py'`. The workflow uses a SHA-pinned official checkout action and requests contents and pull-request write permission for measurement commits and the draft PR. Allow GitHub Actions to create pull requests in repository settings. The scheduled workflow becomes available after its setup PR is merged. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule) for schedule delays and automatic inactivity disabling.

## Fresh instance continuation

The first instance was stopped and later replaced at the user's request. Its [complete run-01 measurements](data/runs/run-01/samples.csv) and [final stopped summary](data/runs/run-01/summary.json) are retained. The old instance was deleted after verifying its private report and authenticated encrypted backup.

The fresh instance resumes with 54 confirmed report identities. The latest `data/samples.csv` and `data/summary.json` contain only this new instance's observations. Confirmed media includes the preserved baseline; network counters and compute estimates belong to the new instance. Do not combine the two runs by subtracting their counters. Prior instance estimates remain in its archived summary. Source-read window remains 16 MiB.

The private dashboard updates from the AWS reporter every 120 seconds and supports hover, touch and keyboard inspection of real rate intervals. After its setup PR is merged, benchmark refresh is programmatic through GitHub Actions; no recurring LLM monitor is required.
