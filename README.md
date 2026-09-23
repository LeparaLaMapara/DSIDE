# DSIDE

**Masepala: know your municipality.** A plain-language, visual site about every
South African municipality: what it is supposed to do, what it did with the
money, how people live there, how safe it is, and what an ordinary resident can
do about it. Zoom from the whole country down to your own ward.

"You are the government. This is your information."

## How it works

```
public APIs  ->  engine/ (Ubunye Engine pipeline, runs once and stops)  ->  web/data/*.json  ->  web/ (static site)
```

| Source | What it gives | How current |
|---|---|---|
| National Treasury, Municipal Money | budgets, audited spending, building spending, wasted money, audits | latest audited year |
| Stats SA Census 2022 (Wazimap API) | water, toilets, electricity, rubbish, housing, schooling | 2022 |
| Youth Explorer (Wazimap API) | young people not in work, school or training | Census 2011, the newest per municipality |
| SAPS crime statistics | murders, sexual offences, drug crime, burglary per police station | latest quarter |
| Stats SA Labour Force Survey | unemployment for metros and provinces | latest quarter |
| Municipal Demarcation Board | every ward, with its profile | 2021 wards |
| Vulekamali | provincial and national building projects with a location | live |

**engine/** is a Python package built on the [Ubunye Engine](https://github.com/ubunye-ai-ecosystems/ubunye_engine)
(pandas backend). Each public source is an Ubunye reader plugin, and the
pipeline in `engine/pipelines/dside/municipal/` has five tasks: ingest money,
ingest people, ingest places, analyse, publish. The analysis is in
`engine/dside_engine/analytics/`:

- `money.py`: a 0 to 100 money handling score against Treasury norms, built
  from the raw cubes because Treasury's ready-made indicators are broken for
  recent years; impossible numbers are flagged, not shown.
- `wellbeing.py`: a wellbeing index after Stats SA's multidimensional poverty
  index, with a 5,000-draw weight test so every rank says how solid it is.
- `compare.py`: peers (metros with metros, rural with rural), strengths and
  problems, and the facts that go with each problem.
- `audit_model.py`: next year's audit chance, published only because it beats
  the "same as last year" guess on a year it never saw (only just; the About
  page says so).
- `local.py`: crime per station and municipality, jobs now, ward facts.

**web/** is a Next.js static site (no server): a national map, one page per
municipality, a ward map with "find my ward", and "what you can do" cards
chosen from each municipality's own problems.

## Run it

```bash
cd engine
pip install -e ".[test]"
pytest -q tests
./run.sh                  # REFRESH=true to ignore the download cache
cd ../web && npm install && npm run build   # output in web/out
```

The data refreshes itself once a quarter through `.github/workflows/refresh-data.yml`.

## The 2017 project

The original DSIDE work (notebooks, Django dashboard, the unfinished
`dside-next` attempt) is kept below and in the older folders for history.

---

# DSIDE - Municipal Money (2017)



<p align="center">
   <img src="MN2.png" style="float: right;" width="500" height="300" />
  <img src="MN.png" width="500" height="300" />
</p>

<p align="center">
  <img src="MN3.png" width="500" height="300" />
</p>


The project was aimed towards aiding municipalities of South Africa to better measure their performance 
in terms of Service Delivery and Efficiency. We achieved this through the creation 
of a *profiling measure*. Furthermore we investigated which youth characteristics are
associated with *youth unemployment*. An extensive tool was developed in the form of a dashboard, 
where the results and real time predictions of the developed models can be viewed.


- We used several machine learning techiques:

* Principal Componet Analysis (PCA): to find the features which affect youth employment.
* Decision Tree and Random Forests : to predictions the probability of youth getting employed given the characteristics of their municipality.
* Support Vector Machines (SVM)    : to predict the profile of the municipality.

- Outputs to the projects:

* [Infographic](https://create.piktochart.com/output/27061299-municipal-money)

* [Presentation](https://prezi.com/view/DltmNuhuwJH3mcKxkPEH/)

- Here is the Link to the data source:

* [Municipal Money Data](https://municipalmoney.gov.za/)
