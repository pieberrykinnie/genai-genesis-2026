# AGENTS.md

**See also:** `projectspec.md` (full API, data sources §3, ML), `projectoverview.md` (pitch, judging, award), `README.md` (quickstart), `.cursor/rules/` (project-reference.mdc, frontend-only.mdc).

## Project Overview
DataSite Impact Analyzer estimates environmental, economic, grid, and sociological impacts of a proposed Canadian data centre. It combines deterministic formulas, ON/AB ML grid-strain prediction, and optional LLM report generation.

## Required Proposal Inputs
Minimum structured inputs (from form/API):
- `address`, `province`
- `it_load_mw`, `pue`, `wue`
- `cooling_type`, `facility_type`
- `capex_cad` (CAD millions), `construction_months`
- `has_onsite_generation`, `renewable_ppa`

## Optional PDF Ingestor
Support an ingestion path where a proposal PDF is parsed into the same schema:
1. Extract text/tables (OCR if needed).
2. Map extracted values to the proposal fields above.
3. Validate ranges and missing fields.
4. Ask user to confirm low-confidence values.

## Data to Pull for Calculations
Use live APIs when available, cache locally, and keep deterministic fallbacks.

### Energy + Grid
- Real-time carbon intensity: Electricity Maps  
  https://portal.electricitymaps.com/docs/getting-started
- Ontario demand history (ML training): IESO Data Directory / demand CSVs  
  https://www.ieso.ca/en/Power-Data/Data-Directory  
  https://reports.ieso.ca/public/Demand/
- Alberta historical market/system data: AESO Data Requests  
  https://www.aeso.ca/market/market-and-system-reporting/data-requests/
- National high-frequency electricity context: CER CCEI HFED guide  
  https://www.canadaenergyregulator.ca/en/data-analysis/canada-energy-future/canadian-centre-energy-information/canadian-centre-energy-information-open-data-user-guide.html

### Community + Demographics
- Census and socio-economic variables (CSD level): StatsCan WDS  
  https://www.statcan.gc.ca/en/developers/wds
- Municipal water use table (denominator for water-share impact): StatsCan table 38-10-0250-01  
  https://www150.statcan.gc.ca/n1/tbl/csv/38-10-0250-01-eng.zip

### Indigenous + Rights/Consultation Signals
- Reserve/land boundary data (for nearest First Nation / treaty context): Open Government datasets  
  https://open.canada.ca/data/en/
- Drinking water advisories context: ISC pages and federal CSV sources  
  https://www.sac-isc.gc.ca/eng/1506514143353/1533317130660

### Water/Environmental Stress
- Drought severity baseline: Canadian Drought Monitor (AAFC)  
  https://agriculture.canada.ca/en/agricultural-production/weather/canadian-drought-monitor
- AQHI baseline: ECCC/MSC open AQHI feeds  
  https://eccc-msc.github.io/open-data/msc-data/aqhi/readme_aqhi_en/

### Nearest Water Source (recommended add-on)
- Compute nearest river/lake to site for water-risk context using hydrography datasets (GeoGratis/Open Canada).  
  https://open.canada.ca/data/en/  
  https://geogratis.gc.ca/

## Practical Rules
- Keep source freshness timestamps in every assessment response.
- Prefer ON+AB high-fidelity + fallback tables for other provinces.
- Never block core scoring if one external API is down.
