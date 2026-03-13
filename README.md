# Underpaid to Measure? Efficiency Wages and Data Quality in the National Forest Inventory

Replication code and analysis for a study of ocular estimation behavior in
the USDA Forest Inventory and Analysis (FIA) program, motivated by an
efficiency wage model calibrated to federal seasonal pay scales.

## Requirements

- Python >= 3.9
- Packages: `pip install -r requirements.txt`
- For PDF assembly: Times New Roman font (pre-installed on macOS and Windows;
  on Linux install `ttf-mscorefonts-installer` or the script falls back to
  built-in Times-Roman)

## Data Acquisition

Two external datasets are required. Both are publicly available and can be
downloaded with the provided scripts.

### 1. FIA State Databases (~28 GB total)

Eight state-level SQLite databases from the
[FIA DataMart](https://apps.fs.usda.gov/fia/datamart/):
MN, WI, VT, ME, GA, CO, OR, WA.

```bash
python analysis/download_fia.py
```

Downloads are skipped for states already present in `data/`.

### 2. Yanai et al. (2023) Paired QA Dataset (~32 MB)

Paired quality-assurance and production crew tree measurements from 24
northern states, 2011-2016.

> Yanai, R.D., et al. (2023). *Data for Quantifying Uncertainty in
> Estimation of Tree Attributes.* Forest Service Research Data Archive.
> https://doi.org/10.2737/RDS-2022-0056

```bash
python analysis/download_yanai.py
```

If automatic download is blocked by the USFS server, the script prints
manual instructions. The required files are `Data/Tree.csv` and
`Data/Plot.csv`, placed in `data/yanai_paired/`.

## Execution Order

Run scripts from the project root directory. Steps at the same level are
independent and can be run in parallel.

```
Step 1:  python analysis/download_fia.py        # download FIA databases
         python analysis/download_yanai.py       # download Yanai dataset

Step 2:  python analysis/extract_data.py         # build parquet files from SQLite

Step 3 (parallel):
         python analysis/calibration_tables.py   # theoretical model calibration
         python analysis/figures.py              # NSC sensitivity figures
         python analysis/digit_heaping.py        # Analysis 1: digit rounding
         python analysis/allometric_residuals.py # Analysis 2: allometric residuals
         python analysis/qa_comparison.py        # Analysis 3: QA vs production DID
         python analysis/remeasurement_growth.py # Analysis 4: remeasurement anomalies
         python analysis/paired_qa_analysis.py   # Analysis 5: Yanai paired data

Step 4:  python analysis/assemble_docx.py        # assemble Word document
         python analysis/assemble_pdf.py         # assemble PDF document
```

Notes:
- `qa_comparison.py` and `remeasurement_growth.py` query the SQLite
  databases directly (not the parquet intermediates), so they depend on
  Step 1 but not Step 2.
- `paired_qa_analysis.py` reads the Yanai CSV files and is independent of
  the FIA pipeline.
- `calibration_tables.py` and `figures.py` perform pure computation with
  no data file dependencies.

## Project Structure

```
analysis/               Python scripts (see execution order above)
revised/                Markdown drafts of each paper section
data/                   Raw data (not tracked — see Data Acquisition)
  fia_qa_summary.csv    Small summary CSV (tracked)
tables/                 Generated CSV tables (not tracked)
figures/                Generated figures (not tracked)
```

## Outputs

Running the full pipeline produces:

- **21 CSV tables** in `tables/` with all regression results, descriptive
  statistics, and calibration parameters
- **10 figure pairs** (PNG + PDF) in `figures/`
- **Underpaid_to_Measure_revised.docx** and **.pdf** in the project root

All numerical values cited in the paper are traceable to the CSV outputs.

## Reproducibility

- The only stochastic element is the wild cluster bootstrap in
  `qa_comparison.py`, which uses a fixed seed (`numpy.random.default_rng(42)`)
  for exact reproducibility.
- All other computations are deterministic given the same input data.
- FIA DataMart databases are periodically updated by USFS. Results were
  produced using databases downloaded in early 2025; subsequent data
  revisions may produce slightly different counts.

## License

Code is released under the [MIT License](LICENSE). The FIA and Yanai
datasets are subject to their own terms from the USDA Forest Service.
# Underpaid-to-Measure-Efficiency-Wages-and-Data-Quality-in-the-National-Forest-Inventory
