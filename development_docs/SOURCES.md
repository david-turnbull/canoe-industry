# canoe-industry — External Data Sources

For human reference. Not consumed by any tooling.

| Source | What it provides | Accessed by | Cache file |
|---|---|---|---|
| NRCan Comprehensive Energy Use Database — `https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/showTable.cfm` | Sector energy use (PJ) by province and fuel type for each industrial subsector (NRCan aggregate tables 2–12, provinces: ON, AB, QC, BC, MB, SK, ATL). Baseline year configurable via `nrcan_year` in `params.yaml`. | `data_scraper.load_cached_or_fetch_industry` | `cache/dataframes.pkl` |
| CER Canada Energy Futures 2023 — `https://www.cer-rec.gc.ca/open/energy/energyfutures2023/macro-indicators-2023.csv` | Macro-economic indicators (GDP by scenario/year) used to scale baseline energy demand forward to model periods. Scenario and variable name are configurable in `params.yaml`. | `data_scraper.load_cached_or_fetch_industry` | `cache/macro_df.pkl` |
| Statistics Canada table 25-10-0029-01 — `https://www150.statcan.gc.ca/n1/tbl/csv/25100029-eng.zip` | Energy use by sector and Atlantic province (NL, NB, NS, PEI), used to disaggregate the NRCan ATL aggregate into individual province shares. | `statcan.load_statcan_atl_shares` | `cache/statcan_atl.pkl` |

## Notes

- All three sources are cached to disk on first fetch; subsequent runs read from cache.
  Delete the relevant `.pkl` file to force a refresh.
- The CER URL is pinned to the 2023 edition. If a newer edition is published,
  update `CER_URL` in `data_scraper.py` and clear `cache/macro_df.pkl`.
- NRCan and StatCan are fetched at runtime; no API keys required.
- The NRCan and StatCan sources are also used by `canoe-agriculture` (same endpoints,
  different table/column selections). Worth noting if a shared fetch layer is ever built.
