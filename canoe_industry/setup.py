# -*- coding: utf-8 -*-
"""
Created on Thu Aug 14 19:26:36 2025

@author: david
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict
import pandas as pd
from canoe_industry.common import setup_logging, load_yaml, project_paths

logger = setup_logging()


class Config:
    def __init__(self, params: dict):
        self.params = params

    @property
    def schema_version(self) -> int:
        v = self.params.get("schema_version", "3.2")
        return str(v)

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



def create_empty_comb_dict(db_path: Path, tables: list[str]) -> Dict[str, pd.DataFrame]:
    comb_dict: Dict[str, pd.DataFrame] = {}
    with sqlite3.connect(db_path) as conn:
        for table in tables:
            cols = conn.execute(f"PRAGMA table_info('{table}');").fetchall()
            col_names = [c[1] for c in cols]
            comb_dict[table] = pd.DataFrame(columns=col_names)
    return comb_dict


def load_runtime_industry(temp_db_name: str = "CAN_industry.sqlite") -> tuple[Path, Config, list[str], Dict[str, pd.DataFrame]]:
    paths = project_paths()
    params = load_yaml(paths["input"] / "params.yaml")
    cfg = Config(params)

    # Domain constants (from your original setup)
    sector_abv = "I_"
    sector_list = ['CON', 'PULP', 'SMELT', 'REFINING', 'CEMENT', 'CHEM', 'STEEL', 'OTH_MAN', 'FOR', 'MINING']
    sector_list_ex = ['Construction', 'Pulp and paper', 'Smelting', 'Petroleum refining', 'Cement', 'Chemical', 'Iron and Steel', 'Other manufacturing', 'Forestry', 'Mining and Oil & Gas extraction']
    province_list = cfg.province_list
    commodity_list = ['elc', 'ng', 'dsl', 'hfo', 'pcoke', 'ngl', 'coal', 'coke', 'wood', 'oth']
    commodity_list_ex = ['Electricity', 'Natural Gas', 'Diesel', 'Heavy Fuel Oil', 'Petroleum Coke', 'Natural Gas Liquids', 'Coal', 'Coke', 'Wood', 'Other']
    atl_pro = ['PEI', 'NB', 'NS', 'NLLAB']

    # Build IDs
    id_dict: dict[str, str] = {p: f"INDHR{p}{cfg.version}" for p in province_list}
    id_dict['CAN'] = f"INDHR{cfg.version}"

    db_path = paths["outputs"] / temp_db_name
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            "canoe-base must create the database before this module runs."
        )
    with sqlite3.connect(db_path) as conn:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()]
    logger.info("Opened existing DB at %s (%d tables)", db_path, len(tables))
    comb_dict = create_empty_comb_dict(db_path, tables)

    # embed domain/meta for downstream modules
    comb_dict["__domain__"] = {
        "sector": "Industry",
        "sector_abv": sector_abv,
        "sector_list": sector_list,
        "sector_list_ex": sector_list_ex,
        "province_list": province_list,
        "commodity_list": commodity_list,
        "commodity_list_ex": commodity_list_ex,
        "atl_pro": atl_pro,
        "periods": cfg.periods,
    }
    comb_dict["__ids__"] = id_dict
    comb_dict["__version__"] = cfg.version

    # Mapping used across modules (from your original)
    comb_dict["__canoe_dem_to_sec__"] = {
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
    }

    return db_path, cfg, tables, comb_dict