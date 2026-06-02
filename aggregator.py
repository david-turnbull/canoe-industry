# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 13:36:00 2025

@author: david
"""
from __future__ import annotations
import argparse
import sqlite3
from typing import Dict
import pandas as pd

from common import setup_logging, project_paths
from setup import load_runtime_industry
from techcom import build_technology_and_commodity_industry
from data_scraper import load_cached_or_fetch_industry
from statcan import load_statcan_atl_shares
from demands import build_demand_and_capacity_industry
#from costs import build_cost_invest_industry
from techinput import build_limit_tech_input_split_industry
from efficiency import build_efficiency_industry
from post_processing import add_datasets_and_sources_industry
from post_processing import add_time_ind, update_ids
logger = setup_logging()


def write_comb_dict_to_db(db_path, tables, comb_dict: Dict[str, pd.DataFrame]) -> None:
    with sqlite3.connect(db_path) as conn:
        for table in tables:
            df = comb_dict.get(table)
            if df is None or df.empty:
                logger.warning("Skipping table with no rows: %s", table)
                continue
            df.to_sql(table, conn, if_exists="append", index=False)
            logger.info("Wrote %d rows to %s", len(df), table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Industry ETL Aggregator")
    parser.add_argument("--db-name", default="CAN_industry.sqlite", help="Output SQLite filename")
    args = parser.parse_args()

    # Initialize DB + comb_dict
    db_path, cfg, tables, comb_dict = load_runtime_industry(temp_db_name=args.db_name)

    # 1) Tech & Commodity scaffolding
    comb_dict = build_technology_and_commodity_industry(comb_dict)

    # 2) External data (NRCan/CER)
    loaded_df, pop_df = load_cached_or_fetch_industry(cfg.nrcan_year, project_paths()['cache'])

    # 3) StatCan ATL shares
    atl_shares = load_statcan_atl_shares(project_paths()['cache'])

    # 4) Demand + ExistingCapacity (includes ATL allocation and GDP scaling)
    comb_dict = build_demand_and_capacity_industry(comb_dict, loaded_df, pop_df, atl_shares)

    # 5) LimitTechInputSplitAnnual from NRCan share tables (with ATL presence gating)
    comb_dict = build_limit_tech_input_split_industry(comb_dict, loaded_df, atl_shares)

    # 6) Efficiency derived from techinput mapping
    comb_dict = build_efficiency_industry(comb_dict)

    # 7) Costs (simple placeholder; gated upstream by presence already)
    #comb_dict = build_cost_invest_industry(comb_dict)

    # 8) DataSet + DataSource
    comb_dict = add_datasets_and_sources_industry(comb_dict)
    #9) Add testing parameters including time and region
    comb_dict = add_time_ind(comb_dict)
    #comb_dict= update_ids(comb_dict)
    # 9) Persist
    write_comb_dict_to_db(db_path, tables, comb_dict)
    logger.info("Done. SQLite written to %s", db_path)


if __name__ == "__main__":
    main()