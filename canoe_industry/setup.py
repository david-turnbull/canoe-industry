# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import tomllib
from pydantic import BaseModel, ConfigDict
from canoe_industry.common import setup_logging, project_paths

logger = setup_logging()


class CANOEInputFuel(BaseModel):
    shortname: str
    longname: str
    nrcan_col_idx: int


class CANOEIndustrySector(BaseModel):
    shortname: str
    longname: str
    nrcan_table_idx: int
    canoe_dem_key: str
    statcan_sector_name: str


class DataQualityProfile(BaseModel):
    dq_cred: int
    dq_geog: int
    dq_struc: int
    dq_tech: int
    dq_time: int


class CANOEIndustryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "4.0"
    version: str
    db_dir: str = "outputs"
    future_periods: list[int]
    province_list: list[str]  # TODO: CANOEProvince — see canoe-agriculture
    atl_provinces: list[str]
    validation_behavior: Literal["error", "warning"] = "error"
    nrcan_year: int = 2022
    gdp_scenario: str = "Global Net-zero"
    gdp_variable: str = "Real Gross Domestic Product ($2012 Millions)"
    input_fuels: list[CANOEInputFuel]
    sectors: list[CANOEIndustrySector]
    dq_demand: DataQualityProfile
    dq_limit_tech_input: DataQualityProfile

    @property
    def formatted_version(self) -> str:
        return f"{int(self.version):03d}"

    @property
    def periods(self) -> list[int]:
        return self.future_periods

    @classmethod
    def validate_from_toml(cls, config_dir: str | Path = ".") -> "CANOEIndustryConfig":
        config_path = Path(config_dir) / "canoe_industry.toml"
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)


@dataclass
class CANOEIndustryRuntime:
    """Typed runtime context derived from CANOEIndustryConfig.

    Computed once at startup; passed by reference to every builder function.
    Replaces the untyped `meta: dict` anti-pattern.
    """
    cfg: CANOEIndustryConfig
    db_path: Path

    # Lookup tables and ID maps — derived once in __post_init__
    ids: dict[str, str] = field(init=False)
    sector_list: list[str] = field(init=False)
    sector_list_ex: list[str] = field(init=False)
    commodity_list: list[str] = field(init=False)
    commodity_list_ex: list[str] = field(init=False)
    demand_com_list: list[str] = field(init=False)
    sector_table_map: dict[str, int] = field(init=False)
    com_to_col: dict[str, int] = field(init=False)
    canoe_dem_to_sec: dict[str, str] = field(init=False)

    def __post_init__(self) -> None:
        fv = self.cfg.formatted_version
        self.ids = {p: f"INDHR{p}{fv}" for p in self.cfg.province_list}
        self.ids["CAN"] = f"INDHR{fv}"
        self.sector_list = [s.shortname for s in self.cfg.sectors]
        self.sector_list_ex = [s.longname for s in self.cfg.sectors]
        self.commodity_list = [f.shortname for f in self.cfg.input_fuels]
        self.commodity_list_ex = [f.longname for f in self.cfg.input_fuels]
        self.demand_com_list = [f"D_{s.shortname}" for s in self.cfg.sectors]
        self.sector_table_map = {s.shortname: s.nrcan_table_idx for s in self.cfg.sectors}
        self.com_to_col = {f.shortname: f.nrcan_col_idx for f in self.cfg.input_fuels}
        self.canoe_dem_to_sec = {s.canoe_dem_key: s.statcan_sector_name for s in self.cfg.sectors}

    # Thin delegates to cfg — spares callers from going through .cfg for common fields
    @property
    def sector_abv(self) -> str:
        return "I_"

    @property
    def province_list(self) -> list[str]:
        return self.cfg.province_list

    @property
    def atl_pro(self) -> set[str]:
        return set(self.cfg.atl_provinces)

    @property
    def periods(self) -> list[int]:
        return self.cfg.future_periods

    @property
    def version(self) -> str:
        return self.cfg.formatted_version

    @property
    def nrcan_year(self) -> int:
        return self.cfg.nrcan_year

    @property
    def gdp_scenario(self) -> str:
        return self.cfg.gdp_scenario

    @property
    def gdp_variable(self) -> str:
        return self.cfg.gdp_variable

    @property
    def dq_demand(self) -> DataQualityProfile:
        return self.cfg.dq_demand

    @property
    def dq_limit_tech_input(self) -> DataQualityProfile:
        return self.cfg.dq_limit_tech_input


def load_runtime_industry(
    temp_db_name: str = "CAN_industry.sqlite",
) -> CANOEIndustryRuntime:
    paths = project_paths()
    cfg = CANOEIndustryConfig.validate_from_toml(paths["root"])

    db_path = paths["root"] / cfg.db_dir / temp_db_name
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            "canoe-base must create the database before this module runs."
        )
    logger.info("Opened existing DB at %s", db_path)

    return CANOEIndustryRuntime(cfg=cfg, db_path=db_path)
