import pandas as pd
from typing import Iterable, Optional, Set
from pydantic.dataclasses import dataclass
import dataclasses
import datetime as dt
import math


@dataclass(frozen=True, eq=False)
class Asset:
    name: str
    site_code: str
    asset_key: str
    type: str
    image: str
    launch_date: dt.datetime
    capacities: dict
    min_capacities: Optional[dict] = None

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __o: object) -> bool:
        return self.name == __o.name

    @classmethod
    def from_record(cls, capacity: dict, commitments: Optional[dict] = None):
        site = capacity.pop("Asset")
        default = (
            site,
            capacity.pop("Site_Code"),
            capacity.pop("Asset_Key"),
            capacity.pop("Type"),
            capacity.pop("Image"),
            dt.datetime(
                year=capacity.pop("Launch_Year"),
                month=capacity.pop("Launch_Month"),
                day=1,
            ),
            capacity,
        )

        return cls(*default, commitments[site]) if commitments else cls(*default)


@dataclass(frozen=True, eq=True)
class Sku:
    date: dt.datetime
    material_number: str
    image: str
    config: str
    region: str
    market: str
    country_id: str
    product: str
    product_id: str
    doses: int
    batches: float
    allocated_to: Optional[Asset] = dataclasses.field(default_factory=lambda: None)
    percent_utilization: Optional[float] = dataclasses.field(
        default_factory=lambda: None
    )

    @classmethod
    def from_tuple(cls, t):
        return cls(*t)

    def to_dict(self):
        dictionary = dataclasses.asdict(self)
        dictionary["year"] = self.date.year
        del dictionary["date"]
        del dictionary["batches"]
        if self.allocated_to:
            dictionary["site"] = self.allocated_to.name
            dictionary["site_code"] = self.allocated_to.site_code
            dictionary["asset_key"] = self.allocated_to.asset_key
            del dictionary["allocated_to"]
        return dictionary

    def to_aws(self):
        base_dict = {
            "plant_id": self.allocated_to.site_code,
            "mtrl_id": self.material_number,
            "rsrc_group": self.allocated_to.asset_key,
            "frcst_yr": self.date.year,
            "prod_fmly_cd": self.product_id,
            "image": self.image,
            "config": self.config,
            "cntry": self.country_id,
            "prdctn_qty": self.doses,
            "util": self.percent_utilization,
            "Run_hrs": self.allocated_to.capacities.get(str(self.date.year), 0)
            * self.percent_utilization,
            "max_cap": self.allocated_to.capacities.get(str(self.date.year), 0),
            "min_cnstrnt": 0,
        }
        if self.allocated_to.min_capacities:
            base_dict["min_cnstrnt"] = self.allocated_to.min_capacities[self.date.year]
        return base_dict

    def to_tuple(self):
        return (
            (
                self.date.year,
                self.image,
                self.config,
                self.region,
                self.market,
                self.country_id,
                self.product,
                self.product_id,
                self.doses,
                self.allocated_to.name,
                self.allocated_to.site_code,
                self.allocated_to.asset_key,
                self.percent_utilization,
            )
            if self.allocated_to
            else dataclasses.astuple(self)
        )

    def __gt__(self, other):
        return self.doses > other.doses


Sku.__pydantic_model__.update_forward_refs()

DAYS_IN_A_MONTH = 30.16
MONTHS_IN_A_YEAR = 12


class Demand(set):
    def __init__(self, lrop: dict, months_to_offset: int = 0, monthize_capacity=False):
        lrop = pd.DataFrame(lrop)
        self.data: Set[Sku] = set()
        if monthize_capacity:
            for month in range(1, 13):
                for t in lrop.itertuples(index=False):
                    (year, *rest, doses, batches) = t
                    self.data.add(
                        Sku.from_tuple(
                            (
                                dt.datetime(year=year, month=month, day=1)
                                - dt.timedelta(
                                    days=(DAYS_IN_A_MONTH * months_to_offset)
                                ),
                                *rest,
                                math.ceil(doses / MONTHS_IN_A_YEAR),
                                batches,
                            )
                        )
                    )
        else:
            for t in lrop.itertuples(index=False):
                (year, *rest) = t
                self.data.add(
                    Sku.from_tuple((dt.datetime(year=year, month=1, day=1), *rest))
                )
        self.monthize_capacity = monthize_capacity

    def demand_for_date(self, year: int, month: Optional[int] = None) -> Iterable[Sku]:
        for sku in self.data:
            if self.monthize_capacity:
                if sku.date.year == year and sku.date.month == month:
                    yield sku
            elif sku.date.year == year:
                yield sku
