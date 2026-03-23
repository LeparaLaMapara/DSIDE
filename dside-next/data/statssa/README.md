# StatsSA QLFS Data

## Downloading Quarterly Labour Force Survey microdata

StatsSA does not provide a public REST API for QLFS data. You need to download
the data manually and place the files in this directory.

### Steps

1. Visit the StatsSA publications page:
   **https://www.statssa.gov.za/publications/P0211/**

2. Download the latest Quarterly Labour Force Survey (QLFS) release.
   Files are typically published as Excel (.xlsx) or CSV attachments.

3. For microdata access (individual-level records), apply through the
   StatsSA Nesstar portal:
   **https://interactive2.statssa.gov.za/webapi/jsf/login.xhtml**

4. Place downloaded CSV or Excel files in this directory
   (`dside-next/data/statssa/`).

### Expected file format

The ingestion script (`ingest_statssa.py`) will attempt to detect columns
automatically. For best results, ensure your files include these columns
(names are flexible — the script uses heuristic matching):

| Column                | Description                          |
|-----------------------|--------------------------------------|
| province / geography  | Province or municipality name        |
| year / period         | Year of the survey                   |
| quarter               | Quarter number (1–4)                 |
| unemployment_rate     | Official unemployment rate (%)       |
| youth_unemployment    | Youth (15–34) unemployment rate (%)  |
| neet_rate             | NEET rate (%)                        |
| absorption_rate       | Absorption rate (%)                  |

### Useful publications

- **P0211** — Quarterly Labour Force Survey
- **P0302** — Mid-year Population Estimates
- **P0318** — General Household Survey
- **Census 2022** — https://census.statssa.gov.za/
