# Planning AWS credit use

For this USD 24/month Lightsail bundle, a simple compute approximation is:

```text
server estimate = runtime days × 24 / 30
combined traffic = archive bytes read + media bytes sent + retries and overhead
```

| Runtime | Approximate server credits |
| --- | ---: |
| 7 days | USD 5.60 |
| 14 days | USD 11.20 |
| 30 days | USD 24.00 |
| 60 days | USD 48.00 |

These are scenarios, not measured completion costs. Billing is hourly with a calendar-month cap; the 30-day formula is approximate. A stopped instance remains billable until deleted.

Reading 903 GB and sending a similar amount gives about 1.8 TB combined before retries and range-read overhead. Both directions consume Lightsail's allowance, but only excess outgoing traffic is charged. Sydney receives half the standard advertised allowance. Confirm the effective allowance for the actual instance and billing dates; do not assume that a short-lived instance receives an unrestricted full-month allowance.

For conservative planning, model outbound overage at USD 0.17/GB in Sydney and retain credit headroom. There is no general guarantee that `max(0, in+out-allowance)` equals the billed overage, because only outbound traffic beyond allowance is charged. Use AWS billing for the final result.

Regular US EC2 internet egress has an account-wide monthly free allowance and then a per-GB charge. Spot discounts compute rather than internet traffic. Do not choose a small instance solely from its hourly CPU price when moving hundreds of GB out to Google.

Avoid duplicating the library into S3 or provisioning a disk for the whole collection when seekable ZIP range access is available. Preserve report identities and native hash checking to reduce repeated work. A traffic ceiling protects against uncontrolled retries, but it is not an exact dollar cap.

See the live dataset for measured elapsed time and traffic; no reliable whole-run ETA is claimed from early startup samples.
