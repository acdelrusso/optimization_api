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
    capacities: dict

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __o: object) -> bool:
        return self.name == __o.name

    @classmethod
    def from_record(cls, capacity: dict):
        return cls(
            capacity.pop("Asset"),
            capacity.pop("Site_Code"),
            capacity.pop("Asset_Key"),
            capacity.pop("Type"),
            capacity.pop("Image"),
            capacity,
        )


@dataclass(frozen=True, eq=True)
class Sku:
    year: int
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
        if self.allocated_to:
            dictionary["allocated_to"] = self.allocated_to.name
        return dictionary

    def to_tuple(self):
        return (
            (
                self.year,
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
    def __init__(
        self, lrop: pd.DataFrame, months_to_offset: int = 0, monthize_capacity=False
    ):
        self.data: Set[Sku] = set()
        if monthize_capacity:
            for month in range(1, 13):
                self.data.update(
                    {
                        Sku.from_tuple(
                            dt.datetime(year=year, month=month, day=1)
                            - dt.timedelta(days=(DAYS_IN_A_MONTH * months_to_offset)),
                            *rest,
                            math.ceil(doses / MONTHS_IN_A_YEAR)
                        )
                        for t in lrop.itertuples(index=False)
                        for (year, *rest, doses) in t
                    }
                )
        else:
            self.data = {Sku.from_tuple(t) for t in lrop.itertuples(index=False)}
        self.monthize_capacity = monthize_capacity
        
    def demand_for_date(self, year: int, month: Optional[int]=None) -> Iterable[Sku]:
        for sku in self.data:
            if self.monthize_capacity:
                if sku.date.year == year and sku.date.month == month:
                    yield sku
            elif sku.year == year:
                yield sku
        