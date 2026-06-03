from __future__ import annotations
from pathlib import Path
import pickle
import requests
import zipfile
import io
import pandas as pd

from canoe_industry.common import setup_logging, ensure_dir

logger = setup_logging()
STATCAN_URL = 'https://www150.statcan.gc.ca/n1/tbl/csv/25100029-eng.zip'

REGION_LIST = ['Newfoundland and Labrador', 'New Brunswick', 'Nova Scotia', 'Prince Edward Island']
SECTOR_LIST = [
    'Total mining and oil and gas extraction', 'Pulp and paper manufacturing', ' Iron and steel manufacturing',
    'Cement manufacturing', 'Aluminum and non-ferrous metal manufacturing', 'Refined petroleum products manufacturing',
    'Chemicals manufacturing', 'All other manufacturing', 'Forestry, logging and support activities', 'Construction'
]
FUEL_LIST = ['Total primary and secondary energy']


def load_statcan_atl_shares(cache_dir: Path) -> dict[str, dict[str, float]]:
    ensure_dir(cache_dir)
    cache_file = cache_dir / 'statcan_atl.pkl'

    if cache_file.exists():
        logger.info("StatCan ATL cache hit: %s", cache_file)
        return pickle.loads(cache_file.read_bytes())

    try:
        r = requests.get(STATCAN_URL, timeout=60)
        r.raise_for_status()
        zf = zipfile.ZipFile(io.BytesIO(r.content))
        with zf.open('25100029.csv') as csvf:
            df = pd.read_csv(csvf)
    except Exception as e:
        raise RuntimeError(f"Failed to download/read StatCan table: {e}") from e

    df1 = df[['REF_DATE', 'GEO', 'Fuel type', 'Supply and demand characteristics', 'VALUE']].copy()
    df1 = df1[df1['REF_DATE'] == 2023]
    df1 = df1[df1['GEO'].isin(REGION_LIST)]
    df1 = df1[df1['Fuel type'].isin(FUEL_LIST)]
    df1 = df1[df1['Supply and demand characteristics'].isin(SECTOR_LIST)]
    df1 = df1[df1['VALUE'] != 0]

    # Build sector->region share dicts
    value_dict: dict[str, dict[str, float]] = {}
    for sector in SECTOR_LIST:
        sub = df1[df1['Supply and demand characteristics'] == sector]
        total = float(sub['VALUE'].sum())
        shares: dict[str, float] = {}
        for reg, reg_df in sub.groupby('GEO'):
            val = float(reg_df['VALUE'].sum())
            shares[reg] = (val / total) if total else 0.0
        value_dict[sector] = shares

    cache_file.write_bytes(pickle.dumps(value_dict))
    return value_dict