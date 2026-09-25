# Masepala ZA relay

SASSA (`sassa.gov.za`) and DWS (`ws.dws.gov.za`) only answer South African
addresses. Probed on 2026-09-25: from a GitHub runner (Microsoft, Arizona) and
from 39 of 40 test points abroad the connection times out without a reply; from
Johannesburg the same pages load in under half a second.

This small service runs in Google Cloud's Johannesburg region (`africa-south1`),
fetches the page and hands it back. The engine uses it only for those hosts,
and only when `DSIDE_ZA_RELAY` is set (the quarterly workflow sets it; a run on
a South African machine needs nothing).

It is not an open proxy: every request needs the token, and only the hosts in
`ALLOWED` are fetched, redirects included. It scales to zero, so it costs
nothing when idle (a quarterly run is a few requests and a few MB).

| Setting | Where |
|---|---|
| Service | Cloud Run `masepala-za-relay`, project `ubunye-sanbox`, region `africa-south1` |
| Token | Secret Manager `masepala-relay-token`, and GitHub secret `DSIDE_ZA_RELAY_TOKEN` |
| Address | GitHub variable `DSIDE_ZA_RELAY` |

Deploy (from this folder):

    gcloud run deploy masepala-za-relay --project ubunye-sanbox --region africa-south1 \
      --source . --allow-unauthenticated --set-secrets RELAY_TOKEN=masepala-relay-token:latest \
      --min-instances 0 --max-instances 2 --concurrency 4 --memory 1Gi --timeout 900

To add a host, add it to `ALLOWED` here and to `ZA_ONLY_HOSTS` in
`engine/dside_engine/http.py` (or set `DSIDE_ZA_ONLY_HOSTS` for a trial), then deploy.
