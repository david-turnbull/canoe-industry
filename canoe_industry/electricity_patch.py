# -*- coding: utf-8 -*-
from __future__ import annotations

from sqlite3 import Cursor
from typing import Dict

import pandas as pd
from loguru import logger

from canoe_industry.common import CANOEIndustryConfig
from canoe_schema.v4_0.models import Efficiency, LifetimeTech, Technology


def add_electricity_bridge(
    module_config: CANOEAgricultureConfig,
    db_cursor: Cursor,
    comb_dict: Dict[str, pd.DataFrame],
) -> None:
    """Add the electricity-to-agriculture transfer pathway.

    Creates:
        E_elc_dem -> E_A_ELC -> A_elc

    The agriculture end-use technology then consumes A_elc through the normal
    techinput logic:
        A_elc -> A_AGRI -> A_d_agri
    """
    ids = comb_dict["__ids__"]

    sector = module_config.sector_initial.upper()
    transfer_tech = f"E_{sector}_ELC"
    input_comm = "E_elc_dem"
    output_comm = f"{sector}_elc"

    configured_fuels = {fuel.shortname.lower() for fuel in module_config.input_fuels}
    if "elc" not in configured_fuels:
        logger.warning(
            "Electricity bridge skipped because 'elc' is not configured in input_fuels."
        )
        return

    # Technology is global/national in the sector dataset, matching the way
    # the rest of the agriculture technology scaffolding is registered.
    tech_row = Technology(
        tech=transfer_tech,
        flag="p",
        sector="agriculture",
        unlim_cap=1,
        annual=0,
        description="Electricity transfer from the electricity sector to agriculture",
        data_id=ids["CAN"],
    )
    db_cursor.executemany(*Technology.bulk_insert_or_ignore_sql([tech_row]))

    efficiency_rows: list[Efficiency] = []
    lifetime_rows: list[LifetimeTech] = []

    for region in module_config.province_list:
        if region == "CAN":
            continue

        data_id = ids[region]

        for vintage in module_config.future_periods:
            efficiency_rows.append(
                Efficiency(
                    region=region,
                    input_comm=input_comm,
                    tech=transfer_tech,
                    vintage=vintage,
                    output_comm=output_comm,
                    efficiency=1.0,
                    notes="Arbitrary value for electricity transfer technology",
                    data_id=data_id,
                )
            )

        lifetime_rows.append(
            LifetimeTech(
                region=region,
                tech=transfer_tech,
                lifetime=5,
                notes=(
                    "Arbitrary lifetime so the electricity transfer technology "
                    "is renewed as often as needed"
                ),
                data_id=data_id,
            )
        )

    if efficiency_rows:
        db_cursor.executemany(
            *Efficiency.bulk_insert_or_ignore_sql(efficiency_rows)
        )

    if lifetime_rows:
        db_cursor.executemany(
            *LifetimeTech.bulk_insert_or_ignore_sql(lifetime_rows)
        )

    logger.info(
        "Electricity bridge {}: Technology=1, Efficiency={}, LifetimeTech={}",
        transfer_tech,
        len(efficiency_rows),
        len(lifetime_rows),
    )
