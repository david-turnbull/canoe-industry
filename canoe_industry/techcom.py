# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 08:34:22 2025

@author: david
"""
from __future__ import annotations
import sqlite3
from canoe_industry.common import setup_logging
from canoe_industry.setup import CANOEIndustryRuntime
from canoe_schema.v4_0.models import Commodity, Technology

logger = setup_logging()


def build_technology_and_commodity_industry(runtime: CANOEIndustryRuntime, cursor: sqlite3.Cursor) -> None:
    sector_abv = runtime.sector_abv
    sector_list = runtime.sector_list
    sector_list_ex = runtime.sector_list_ex
    commodity_list = runtime.commodity_list
    commodity_list_ex = runtime.commodity_list_ex
    commodity_list_type = runtime.commodity_list_type
    ids = runtime.ids

    tech_rows = [
        Technology(
            tech=sector_abv + sec,
            flag="p",
            sector="industrial",
            unlim_cap=1,
            annual=1,
            reserve=0,
            curtail=0,
            retire=0,
            flex=0,
            exchange=0,
            seas_stor=0,
            description=f"Generic technology representing {sector_list_ex[i]} industry",
            data_id=ids['CAN'],
        )
        for i, sec in enumerate(sector_list)
    ]

    demand_com_list = ["D_" + s for s in sector_list]
    com_list = commodity_list + demand_com_list
    desc_list = commodity_list_ex + sector_list_ex

    comm_rows = []
    for i, com in enumerate(com_list):
        code = sector_abv + com.lower()
        if code.startswith(sector_abv + "d_"):
            flag = "d"
            desc = f"Demand for the {desc_list[i]} sector"
        else:
            flag = commodity_list_type[i]
            desc = f"Represents {desc_list[i]} in the industrial sector"
        comm_rows.append(Commodity(name=code, flag=flag, description=desc, data_id=ids['CAN']))

    cursor.executemany(*Technology.bulk_insert_or_ignore_sql(tech_rows))
    cursor.executemany(*Commodity.bulk_insert_or_ignore_sql(comm_rows))
    logger.info("Built %d Technology and %d Commodity rows", len(tech_rows), len(comm_rows))
