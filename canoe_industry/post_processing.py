# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 13:04:16 2025

@author: david
"""
from __future__ import annotations
from typing import Dict
import pandas as pd
from canoe_industry.common import setup_logging
from canoe_schema.v3_2.models import DataSet, DataSource

logger = setup_logging()


def add_datasets_and_sources_industry(comb_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    dom = comb_dict['__domain__']
    ids = comb_dict['__ids__']

    province_list = dom['province_list']
    version = comb_dict['__version__']

    ds_rows: list[DataSet] = []
    for pro in province_list:
        ds_rows.append(
            DataSet(
                data_id=ids[pro],
                label=f"{pro} - industry - high resolution",
                version=f"v{version}",
                description="2025 annual update",
                status="active",
                author="David Turnbull - david.turnbull1@ucalgary.ca",
                date="2025-08-01",
                changelog="Original sector design",
            )
        )
    ds_rows.append(
        DataSet(
            data_id=ids['CAN'],
            label="industry - high resolution",
            version=f"v{version}",
            description="2025 annual update",
            status="active",
            author="David Turnbull - david.turnbull1@ucalgary.ca",
            date="2025-08-01",
            changelog="Original sector design",
        )
    )

    ds_df = pd.DataFrame(
        [row.model_dump(mode='python') for row in ds_rows],
        columns=comb_dict['DataSet'].columns,
    )
    comb_dict['DataSet'] = pd.concat([comb_dict['DataSet'], ds_df], ignore_index=True)

    src_rows: list[DataSource] = [
        DataSource(source_id='I1', source='NRCan Comprehensive Database, https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/menus/trends/comprehensive_tables/list.cfm', notes='Used the appropriate tables for each sector and province', data_id=ids['CAN']),
        DataSource(source_id='I2', source='NRCan Comprehensive Database, https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/menus/trends/comprehensive_tables/list.cfm; CER Canada Energy Futures report, https://apps.cer-rec.gc.ca/ftrppndc/dflt.aspx?GoCTemplateCulture=en-CA', notes='Global net zero macro-economic indicators', data_id=ids['CAN']),
        DataSource(source_id='I3', source='NRCan Comprehensive Database, https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/menus/trends/comprehensive_tables/list.cfm; Statistics Canada 25-10-0029-01, https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2510002901', notes='ATL presence shares for sectoral allocation', data_id=ids['CAN']),
        DataSource(source_id='I4', source='NRCan Comprehensive Database, https://oee.nrcan.gc.ca/corporate/statistics/neud/dpa/menus/trends/comprehensive_tables/list.cfm; CER Canada Energy Futures report, https://apps.cer-rec.gc.ca/ftrppndc/dflt.aspx?GoCTemplateCulture=en-CA;  Statistics Canada 25-10-0029-01, https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2510002901', notes='Combined reference that uses GDP growth, statcan distribution and NRCan original demands to predict atlantic province demands', data_id=ids['CAN'])
    ]
    src_df = pd.DataFrame(
        [row.model_dump(mode='python') for row in src_rows],
        columns=comb_dict['DataSource'].columns,
    )
    comb_dict['DataSource'] = pd.concat([comb_dict['DataSource'], src_df], ignore_index=True)

    logger.info("Post-processing: %d DataSet, %d DataSource", len(ds_rows), len(src_rows))
    return comb_dict