import dataclasses
import pandas as pd
from typing import Iterable, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .asset import Asset


@dataclasses.dataclass(frozen=True)
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
    allocated_to: Optional["Asset"] = None
    percent_utilization: Optional[float] = None

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


class Demand(set):
    def __init__(self, lrop: pd.DataFrame):
        self.data = {Sku.from_tuple(t) for t in lrop.itertuples(index=False)}

    def demand_for_year(self, year: int) -> Iterable[Sku]:
        for sku in self.data:
            if sku.year == year:
                yield sku
