# -*- coding: utf-8 -*-
from __future__ import annotations

from sqlite3 import Cursor
import sqlite3
from typing import Dict

import pandas as pd
from loguru import logger

from canoe_industry.common import setup_logging
from canoe_schema.v4_0.models import Efficiency, LifetimeTech, Technology

from canoe_industry.setup import CANOEIndustryRuntime

logger = setup_logging()

def add_electricity_bridge_industry(
    runtime: CANOEIndustryRuntime,
    cursor: sqlite3.Cursor,
) -> None:
    """Add the electricity-to-industry transfer pathway.

    Creates:
        E_elc_dem -> E_I_elc -> I_elc

    The normal industry end-use technologies then consume I_elc through
    techinput.py, for example:

        I_elc -> I_<industry subsector> -> I_d_<industry subsector>
    """

    transfer_tech = "E_I_elc"
    input_comm = "E_elc_dem"
    output_comm = "I_elc"

    # techinput.py builds I_<commodity> inputs from runtime.com_to_col.
    # Only create the bridge if electricity is part of the configured
    # industry fuel/commodity mapping.
    configured_fuels = {
        str(commodity).lower()
        for commodity in runtime.com_to_col.keys()
    }

    if "elc" not in configured_fuels:
        logger.warning(
            "Electricity bridge skipped because 'elc' is not present "
            "in runtime.com_to_col."
        )
        return

    technology_rows: list[Technology] = []
    efficiency_rows: list[Efficiency] = []
    lifetime_rows: list[LifetimeTech] = []

    for region in runtime.province_list:
        data_id = runtime.ids[region]

        # Technology is repeated by data_id so that each regional industry
        # dataset contains the transfer technology when data_id is part of
        # the table key.
        technology_rows.append(
            Technology(
                tech=transfer_tech,
                flag="p",
                sector="industry",
                unlim_cap=1,
                annual=0,
                description=(
                    "Electricity transfer from the electricity sector "
                    "to the industry sector"
                ),
                data_id=data_id,
            )
        )

        for vintage in runtime.periods:
            efficiency_rows.append(
                Efficiency(
                    region=region,
                    input_comm=input_comm,
                    tech=transfer_tech,
                    vintage=vintage,
                    output_comm=output_comm,
                    efficiency=1.0,
                    notes="Arbitrary efficiency for electricity transfer technology",
                    data_id=data_id,
                )
            )

        lifetime_rows.append(
            LifetimeTech(
                region=region,
                tech=transfer_tech,
                lifetime=5,
                notes=(
                    "Arbitrary five-year lifetime so the electricity transfer "
                    "technology is renewed as often as needed"
                ),
                data_id=data_id,
            )
        )

    if technology_rows:
        cursor.executemany(
            *Technology.bulk_insert_or_ignore_sql(technology_rows)
        )

    if efficiency_rows:
        cursor.executemany(
            *Efficiency.bulk_insert_or_ignore_sql(efficiency_rows)
        )

    if lifetime_rows:
        cursor.executemany(
            *LifetimeTech.bulk_insert_or_ignore_sql(lifetime_rows)
        )

    logger.info(
        "Electricity bridge %s: Technology=%d, Efficiency=%d, LifetimeTech=%d",
        transfer_tech,
        len(technology_rows),
        len(efficiency_rows),
        len(lifetime_rows),
    )
