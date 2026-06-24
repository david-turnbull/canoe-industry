# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 13:36:00 2025

@author: david
"""
from __future__ import annotations
import argparse
import sqlite3

from canoe_industry.common import setup_logging, project_paths
from canoe_industry.setup import load_runtime_industry
from canoe_industry.validation import validate_db_against_config
from canoe_industry.techcom import build_technology_and_commodity_industry
from canoe_industry.data_scraper import load_cached_or_fetch_industry
from canoe_industry.statcan import load_statcan_atl_shares
from canoe_industry.demands import build_demand_and_capacity_industry
from canoe_industry.techinput import build_limit_tech_and_efficiency_industry
# from canoe_industry.costs import build_cost_invest_industry  # TODO: complete CostInvest migration
from canoe_industry.post_processing import add_datasets_and_sources_industry

logger = setup_logging()


def main() -> None:
    parser = argparse.ArgumentParser(description="Industry ETL Aggregator")
    parser.add_argument("--db-name", default="CAN_industry.sqlite", help="Output SQLite filename")
    args = parser.parse_args()

    db_path, cfg, meta = load_runtime_industry(temp_db_name=args.db_name)

    with sqlite3.connect(db_path) as conn:
        # 0) Validate DB against config
        validate_db_against_config(cfg, conn)

        cur = conn.cursor()

        # 1) Tech & Commodity scaffolding
        build_technology_and_commodity_industry(meta, cur)

        # 2) External data (NRCan/CER)
        loaded_df, macro_df = load_cached_or_fetch_industry(cfg.nrcan_year, project_paths()['cache'])

        # 3) StatCan ATL shares
        atl_shares = load_statcan_atl_shares(project_paths()['cache'])

        # 4) Demand + ExistingCapacity
        build_demand_and_capacity_industry(meta, cur, loaded_df, macro_df, atl_shares)

        # 5) LimitTechInputSplitAnnual + Efficiency (co-constructed)
        build_limit_tech_and_efficiency_industry(meta, cur, loaded_df, atl_shares)

        # 6) Costs (TODO: complete CostInvest migration before uncommenting)
        # build_cost_invest_industry(meta, cur)

        # 7) DataSet + DataSource
        add_datasets_and_sources_industry(meta, cur)

        conn.commit()

    logger.info("Done. SQLite written to %s", db_path)


if __name__ == "__main__":
    main()
