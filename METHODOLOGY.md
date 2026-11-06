# Measurement methodology

The worker reads ZIP directories over signed-in Google Drive HTTP ranges and extracts one supported media entry at a time. It hashes/checks existing media through the native client and writes a confirmation row only when a media key is returned. Failed or uncertain outcomes stop the worker. Resume identities include destination, archive version, member name, CRC and size; these private identifiers are excluded from the public dataset.

The reporter samples every 120 seconds. It records confirmed counts and bytes from complete validated report rows, non-loopback NIC inbound/outbound counters, elapsed time, staging size, inventory progress, failed/unknown outcome counts and estimated compute cost. Directional counters remain cumulative across a host reboot. Rates are differences between consecutive samples divided by their timestamp interval; missing/reset counters should not be interpreted as zero transfer.

Archive inventory counts supported, nonempty, non-symlink entries and their uncompressed sizes from central directories without extracting media. Before every archive is indexed, totals are partial. Metadata JSON files, directories and unsupported extensions are excluded. Byte totals can include duplicate content stored under different archive paths.

The website projects remaining time only after the inventory is complete and at least ten minutes of running observations show confirmed progress. It uses the recent confirmed-byte rate where possible, otherwise the file rate. File mix, commit latency, duplicates, throttling and retries can change this estimate substantially. It is a rough projection, not a completion guarantee.

Numeric history is append-only locally, retried if publication fails, and stored durably in Cloudflare D1. The website displays a bounded recent window and can export full numeric history. Private resume reports are encrypted before cloud backup and never included here. The public exporter whitelists fields and drops account data, file paths, tokens, job identifiers and encrypted report contents.

One account, one region and one workload are represented. Results should not be generalized to all libraries, regions, accounts or future mobile API behavior. There is no final billed cost or full-run throughput result until the run is complete and billing is available.

Temporary metadata inventory and bounded read-only speed probes also consume host network traffic during diagnosis. NIC rates during those windows are not pure media throughput.
