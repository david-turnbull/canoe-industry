# -*- coding: utf-8 -*-
"""
Created on Fri Aug 15 08:34:22 2025

@author: david
"""
from __future__ import annotations
import pandas as pd
from typing import Dict
from canoe_industry.common import setup_logging
import numpy as np

logger = setup_logging()


def build_technology_and_commodity_industry(comb_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    dom = comb_dict["__domain__"]
    ids = comb_dict["__ids__"]

    sector_abv = dom["sector_abv"]
    sector_list = dom["sector_list"]
    sector_list_ex = dom["sector_list_ex"]
    commodity_list = dom["commodity_list"]
    commodity_list_ex = dom["commodity_list_ex"]

    # Technology
    tech_rows = []
    for i, sec in enumerate(sector_list):
        tech_rows.append([
            sector_abv + sec,
            "p",
            "industrial",
            np.nan, np.nan, 1, 1, 0, 0, 0, 0, 0, 0,
            f"Generic technology representing {sector_list_ex[i]} industry",
            ids['CAN'],
        ])
    tech_df = pd.DataFrame(tech_rows, columns=comb_dict["Technology"].columns)
    comb_dict["Technology"] = pd.concat([comb_dict["Technology"], tech_df], ignore_index=True)

    # Commodity (+ demand commodities)
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
            flag = "a"
            desc = f"Represents {desc_list[i]} in the industrial sector"
        comm_rows.append([code, flag, desc, ids['CAN']])

    comm_df = pd.DataFrame(comm_rows, columns=comb_dict["Commodity"].columns)
    comb_dict["Commodity"] = pd.concat([comb_dict["Commodity"], comm_df], ignore_index=True)

    comb_dict["__demand_com_list__"] = demand_com_list
    logger.info("Built %d Technology and %d Commodity rows", len(tech_rows), len(comm_rows))
    return comb_dict