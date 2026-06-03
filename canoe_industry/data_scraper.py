# -*- coding: utf-8 -*-
"""
Created on Wed Aug 13 10:50:43 2025

@author: david
"""
from __future__ import annotations
from io import StringIO
from pathlib import Path
import pickle
from typing import Dict
import requests
import pandas as pd

from canoe_industry.common import setup_logging, ensure_dir

logger = setup_logging()

NRCan_URL = "https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/showTable.cfm"
CER_URL = "https://www.cer-rec.gc.ca/open/energy/energyfutures2023/macro-indicators-2023.csv"

TABLE_LIST = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # mirrors your original indices
PROV_CODES = ['on', 'ab', 'qc', 'bct', 'mb', 'sk', 'atl']


def _session(timeout: int = 45) -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "industry-etl/1.0"})
    s.timeout = timeout
    return s


def load_cached_or_fetch_industry(nrcan_year: int, cache_dir: Path) -> tuple[Dict[str, dict[int, pd.DataFrame]], pd.DataFrame]:
    ensure_dir(cache_dir)
    df_cache = cache_dir / "dataframes.pkl"
    pop_cache = cache_dir / "pop_df.pkl"

    if df_cache.exists():
        logger.info("Cache hit: %s", df_cache)
        loaded_df = pickle.loads(df_cache.read_bytes())
    else:
        logger.info("Fetching NRCan aggregated tables (industry)")
        sess = _session()
        dicts: Dict[str, dict[int, pd.DataFrame]] = {k: {} for k in ['AB', 'MB', 'BC', 'SK', 'ON', 'QC', 'ATL']}
        for code in PROV_CODES:
            for rn in TABLE_LIST:
                params = {"type": "CP", "sector": "agg", "juris": code, "year": nrcan_year, "rn": rn, "page": "0"}
                r = sess.get(NRCan_URL, params=params, timeout=45)
                r.raise_for_status()
                tables = pd.read_html(StringIO(r.text))
                if not tables:
                    raise ValueError(f"No tables found for {code} rn={rn}")
                df = tables[0]
                # route to model code
                if code == 'ab':
                    dicts['AB'][rn] = df
                elif code == 'on':
                    dicts['ON'][rn] = df
                elif code == 'bct':
                    dicts['BC'][rn] = df
                elif code == 'mb':
                    dicts['MB'][rn] = df
                elif code == 'sk':
                    dicts['SK'][rn] = df
                elif code == 'qc':
                    dicts['QC'][rn] = df
                elif code == 'atl':
                    dicts['ATL'][rn] = df
        loaded_df = dicts
        df_cache.write_bytes(pickle.dumps(loaded_df))

    if pop_cache.exists():
        logger.info("Cache hit: %s", pop_cache)
        pop_df = pickle.loads(pop_cache.read_bytes())
    else:
        sess = _session()
        r = sess.get(CER_URL, timeout=45)
        r.raise_for_status()
        pop_df = pd.read_csv(StringIO(r.text))
        pop_cache.write_bytes(pickle.dumps(pop_df))

    return loaded_df, pop_df