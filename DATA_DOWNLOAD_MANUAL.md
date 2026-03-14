# Manual Data Download Guide (No Playwright)

This guide gives click-by-click and command-by-command steps to get the data into this repo.

## 1) Folder setup

1. Open PowerShell.
2. Go to backend:

```powershell
cd E:\Adi\Work\project\genisys-hack\genai-genesis-2026\backend
```

3. Ensure data folder exists:

```powershell
New-Item -ItemType Directory -Force .\data | Out-Null
```

All downloaded files should end up under `backend/data/`.

## 2) IESO demand data (Ontario)

Sources:
- Data Directory: https://www.ieso.ca/en/Power-Data/Data-Directory
- Public reports index: https://reports.ieso.ca/public/Demand/

Steps:
1. Open the IESO Data Directory page.
2. Click `Demand`.
3. Click `Hourly Electricity Consumption Data`.
4. Download yearly files named like `PUB_Demand_YYYY.csv`.
5. Save each file to `backend/data/` with the same filename.

Minimum recommended years for model training:
- `PUB_Demand_2020.csv`
- `PUB_Demand_2021.csv`
- `PUB_Demand_2022.csv`
- `PUB_Demand_2023.csv`
- `PUB_Demand_2024.csv`
- `PUB_Demand_2025.csv` (if available)
- `PUB_Demand_2026.csv` (if available)

Validate each file is real CSV (not HTML):

```powershell
Get-Content .\data\PUB_Demand_2024.csv -TotalCount 3
```

If the first line contains `<html>`, redownload from browser directly.

## 2b) IESO hourly consumption by FSA (monthly ZIP files)

Source:
- https://reports-public.ieso.ca/public/HourlyConsumptionByFSA/

Use the script:

```powershell
.\.venv\Scripts\python.exe scripts\download_ieso_hourly_fsa.py --list-only --latest-months 12 --no-manifest
```

Download the last 24 months:

```powershell
.\.venv\Scripts\python.exe scripts\download_ieso_hourly_fsa.py --latest-months 24 --out-dir .\data\fsa_monthly
```

Download a fixed range:

```powershell
.\.venv\Scripts\python.exe scripts\download_ieso_hourly_fsa.py --from-ym 202401 --to-ym 202412 --out-dir .\data\fsa_monthly
```

Output files look like:
- `PUB_HourlyConsumptionByFSA_202511_v1.zip`

## 3) AESO demand/grid data (Alberta)

Source:
- https://www.aeso.ca/market/market-and-system-reporting/data-requests/

Use these sections first:
- `Current and Historical Market Data and Reports`
- `Price & Alberta Internal Load (AIL)`
- `System & regional load`
- `Generation`
- `Historical Generation Data (CSD)`

Steps:
1. Download hourly CSV/XLSX files that include Alberta load/demand (`AIL`, `system load`, or equivalent).
2. If download is XLSX, export to CSV.
3. Save in `backend/data/` as:
   - `aeso_2020.csv`
   - `aeso_2021.csv`
   - `aeso_2022.csv`
   - `aeso_2023.csv`
   - etc.

Note:
- Some AESO data is request-only through `manalysis@aeso.ca` and may take 10-15 business days with potential fees. For MVP/hackathon, prioritize publicly posted files.

## 4) StatsCan (reliable method via WDS API -> ZIP download)

Do not hardcode old ZIP URLs. Use WDS API to get the current download links.

From `backend`:

```powershell
$u1 = (Invoke-RestMethod "https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/98100001/en").object
$u2 = (Invoke-RestMethod "https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/38100250/en").object
Invoke-WebRequest -Uri $u1 -OutFile ".\data\98-10-0001-01.zip"
Invoke-WebRequest -Uri $u2 -OutFile ".\data\38-10-0250-01.zip"
```

Load into SQLite:

```powershell
uv run python scripts/load_census_to_sqlite.py --db .\data\census_csd.db --census-csv .\data\98-10-0001-01.zip --water-csv .\data\38-10-0250-01.zip
```

## 5) Train model after data is present

```powershell
uv run python scripts/train_grid_model.py --data-dir .\data --model-out .\models\grid_strain_model.pkl
```

Check artifact metadata:

```powershell
uv run python -c "import joblib; a=joblib.load('./models/grid_strain_model.pkl'); print(a.get('version'), a.get('used_synthetic_data'), a.get('training_rows'))"
```

Expected:
- `used_synthetic_data` should be `False`.

## 6) Run backend and verify live behavior

```powershell
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8010
```

Call assessment and verify:
- `grid_strain.model_version` is not `xgboost_v1_synthetic_fallback`.
- `data_freshness.maptiler_geocoding` shows a timestamp (if MapTiler key is set).
- `data_freshness.grid_carbon_source` shows fallback/source used.

## 7) Quick troubleshooting

If model still trains on synthetic fallback:
1. Confirm files exist:

```powershell
Get-ChildItem .\data\PUB_Demand_20*.csv
Get-ChildItem .\data\aeso_*.csv
```

2. Confirm IESO files are CSV, not HTML.
3. Confirm you ran command from `backend`.
4. Re-run training and artifact metadata check.
