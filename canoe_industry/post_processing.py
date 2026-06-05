# -*- coding: utf-8 -*-
"""
Created on Sun Aug 17 13:04:16 2025

@author: david
"""
from __future__ import annotations
from typing import Dict
import pandas as pd
from canoe_industry.common import setup_logging
from canoe_schema.v3_2.models import (
    DataSet,
    DataSource,
    Region,
    SeasonLabel,
    TimeOfDay,
    TimePeriod,
    TimeSeason,
    TimeSegmentFraction,
)

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
def add_time_ind(comb_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    dom = comb_dict['__domain__']
    periods = dom['periods']
    time_of_day = []
    province_list = dom['province_list']
    x=1
    while x!= 25:
        if x<10:
            time_of_day.append('H0'+str(x))
        else:
            time_of_day.append('H'+str(x))
        x+=1
    time_season = []
    x=1
    while x!=365:
        if x<10:
            time_season.append('D00'+str(x))
        if x>9 and x<100:
            time_season.append('D0'+str(x))
        else:
            time_season.append('D'+str(x))
        x+=1
    tod: list[TimeOfDay] = []
    x=0
    for day in time_of_day:
        tod.append(TimeOfDay(sequence=x, tod=day))
        x+=1
    tp: list[TimePeriod] = []
    x=0
    for period in periods:
        tp.append(TimePeriod(sequence=x, period=period, flag='f'))
        x+=1
    tp.append(TimePeriod(sequence=x, period=2050, flag='f'))
    ts: list[TimeSeason] = []
    for period in periods:
        x=0
        for season in time_season:
            ts.append(TimeSeason(period=period, sequence=x, season=season, notes=''))
            x+=1
    sl: list[SeasonLabel] = []
    for season in time_season:
        sl.append(SeasonLabel(season=season, notes=''))
    tsf: list[TimeSegmentFraction] = []
    for period in periods:
        for season in time_season:
            for day in time_of_day:
                val = float(1/8760)
                tsf.append(TimeSegmentFraction(period=period, season=season, tod=day, segfrac=val, notes=''))
    reg: list[Region] = []
    for region in province_list:
        reg.append(Region(region=region, notes=''))
    tod_df = pd.DataFrame([row.model_dump(mode='python') for row in tod], columns=comb_dict['TimeOfDay'].columns)
    comb_dict['TimeOfDay']= pd.concat([comb_dict['TimeOfDay'], tod_df], ignore_index=True)
    tp_df = pd.DataFrame([row.model_dump(mode='python') for row in tp], columns =comb_dict['TimePeriod'].columns )
    comb_dict['TimePeriod']= pd.concat([comb_dict['TimePeriod'], tp_df], ignore_index=True)
    ts_df = pd.DataFrame([row.model_dump(mode='python') for row in ts], columns =comb_dict['TimeSeason'].columns )
    comb_dict['TimeSeason']= pd.concat([comb_dict['TimeSeason'], ts_df], ignore_index=True)
    sl_df = pd.DataFrame([row.model_dump(mode='python') for row in sl], columns =comb_dict['SeasonLabel'].columns )
    comb_dict['SeasonLabel']= pd.concat([comb_dict['SeasonLabel'], sl_df], ignore_index=True)
    tsf_df =  pd.DataFrame([row.model_dump(mode='python') for row in tsf], columns =comb_dict['TimeSegmentFraction'].columns )
    comb_dict['TimeSegmentFraction']= pd.concat([comb_dict['TimeSegmentFraction'], tsf_df], ignore_index=True)
    reg_df =  pd.DataFrame([row.model_dump(mode='python') for row in reg], columns =comb_dict['Region'].columns )
    comb_dict['Region']= pd.concat([comb_dict['Region'], reg_df], ignore_index=True)
    return comb_dict

def update_ids(comb_dict):
    dom = comb_dict['__domain__']
    province_list = dom['province_list']
    version = comb_dict['__version__']
    province_list.append('CAN')
    sectors = ['CEM', 'CON', 'STEEL', 'PULP', 'SMELT', 'REF', 'CHEM', 'FOR', 'MIN', 'OTH']
    gen_id = {}
    spec_id = {}

    for pro in province_list:
        for sec in sectors:
            if pro == 'CAN':
                val = f"IND{sec}LR{version}"
                gen_id[sec]=(val)
            else:
                val = f"IND{sec}{pro}LR{version}"
                spec_id[pro,sec]=(val)
    comb_dict['Commodity']['data_id']='INDHR001'
    for sec in sectors:
            mask = comb_dict['Technology']['tech'].astype(str).str.contains(
                rf'{sec}', case=True, regex=True, na=False)
            comb_dict['Technology'].loc[mask, 'data_id'] = gen_id[sec]
    for pro in province_list:
        if pro == 'CAN':
            continue
        reg_mask = comb_dict['Demand']['region'].astype(str).eq(pro)
        if not reg_mask.any():
            continue
        for sec in sectors:
            sec_mask = comb_dict['Demand']['commodity'].astype(str).str.contains(rf'{sec}', case=False, regex=True, na=False)
            mask = reg_mask & sec_mask
            comb_dict['Demand'].loc[mask, 'data_id'] = spec_id[pro, sec]
    for pro in province_list:
        if pro == 'CAN':
            continue
        reg_mask = comb_dict['Efficiency']['region'].astype(str).eq(pro)
        if not reg_mask.any():
            continue
        for sec in sectors:
            sec_mask = comb_dict['Efficiency']['tech'].astype(str).str.contains(rf'{sec}', case=False, regex=True, na=False)
            mask = reg_mask & sec_mask
            comb_dict['Efficiency'].loc[mask, 'data_id'] = spec_id[pro, sec]
    for pro in province_list:
        if pro == 'CAN':
            continue
        reg_mask = comb_dict['LimitTechInputSplitAnnual']['region'].astype(str).eq(pro)
        if not reg_mask.any():
            continue
        for sec in sectors:
            sec_mask = comb_dict['LimitTechInputSplitAnnual']['tech'].astype(str).str.contains(rf'{sec}', case=False, regex=True, na=False)
            mask = reg_mask & sec_mask
            comb_dict['LimitTechInputSplitAnnual'].loc[mask, 'data_id'] = spec_id[pro, sec]
    return comb_dict