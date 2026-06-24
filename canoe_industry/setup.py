# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 19:26:36 2025

@author: david
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from canoe_industry.common import setup_logging, load_yaml, project_paths

logger = setup_logging()


class Config:
    def __init__(self, params: dict):
        self.params = params

    @property
    def schema_version(self) -> str:
        return str(self.params.get("schema_version", "4.0"))

    @property
    def version(self) -> str:
        v = self.params.get("version", "1")
        return f"{int(v):03d}"  # "001", "012", "123"

    @property
    def periods(self) -> list[int]:
        return list(self.params.get("periods", [2025]))

    @property
    def nrcan_year(self) -> int:
        return int(self.params.get("NRCan_year", 2022))

    @property
    def future_periods(self) -> list[int]:
        return list(self.params.get("future_periods", self.periods))

    @property
    def province_list(self) -> list[str]:
        return list(self.params.get(
            "province_list",
            ['AB', 'ON', 'BC', 'MB', 'SK', 'QC', 'PEI', 'NB', 'NS', 'NLLAB'],
        ))

    @property
    def validation_behavior(self) -> str:
        return str(self.params.get("validation_behavior", "error"))


def load_runtime_industry(temp_db_name: str = "CAN_industry.sqlite") -> tuple[Path, Config, dict]:
    paths = project_paths()
    params = load_yaml(paths["input"] / "params.yaml")
    cfg = Config(params)

    sector_abv = "I_"
    sector_list = ['CON', 'PULP', 'SMELT', 'REFINING', 'CEMENT', 'CHEM', 'STEEL', 'OTH_MAN', 'FOR', 'MINING']
    sector_list_ex = [
        'Construction', 'Pulp and paper', 'Smelting', 'Petroleum refining',
        'Cement', 'Chemical', 'Iron and Steel', 'Other manufacturing',
        'Forestry', 'Mining and Oil & Gas extraction',
    ]
    commodity_list = ['elc', 'ng', 'dsl', 'hfo', 'pcoke', 'ngl', 'coal', 'coke', 'wood', 'oth']
    commodity_list_ex = [
        'Electricity', 'Natural Gas', 'Diesel', 'Heavy Fuel Oil', 'Petroleum Coke',
        'Natural Gas Liquids', 'Coal', 'Coke', 'Wood', 'Other',
    ]
    atl_pro = ['PEI', 'NB', 'NS', 'NLLAB']

    ids: dict[str, str] = {p: f"INDHR{p}{cfg.version}" for p in cfg.province_list}
    ids['CAN'] = f"INDHR{cfg.version}"

    db_path = paths["outputs"] / temp_db_name
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            "canoe-base must create the database before this module runs."
        )
    logger.info("Opened existing DB at %s", db_path)

    meta: dict = {
        "sector_abv": sector_abv,
        "sector_list": sector_list,
        "sector_list_ex": sector_list_ex,
        "province_list": cfg.province_list,
        "commodity_list": commodity_list,
        "commodity_list_ex": commodity_list_ex,
        "atl_pro": atl_pro,
        "periods": cfg.future_periods,
        "ids": ids,
        "version": cfg.version,
        "canoe_dem_to_sec": {
            "D_CON": "Construction",
            "D_PULP": "Pulp and paper manufacturing",
            "D_SMELT": "Aluminum and non-ferrous metal manufacturing",
            "D_REFINING": "Refined petroleum products manufacturing",
            "D_CEMENT": "Cement manufacturing",
            "D_CHEM": "Chemicals manufacturing",
            "D_STEEL": " Iron and steel manufacturing",
            "D_OTH_MAN": "All other manufacturing",
            "D_FOR": "Forestry, logging and support activities",
            "D_MINING": "Total mining and oil and gas extraction",
        },
    }

    return db_path, cfg, meta
