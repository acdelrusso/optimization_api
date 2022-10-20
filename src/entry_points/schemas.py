from pydantic import BaseModel  # pragma: no cover


class Asset(BaseModel):  # pragma: no cover
    name: str
    site_code: str
    asset_key: str
    type: str
    image: str
    capacities: dict


class Sku(BaseModel):  # pragma: no cover
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
    allocated_to: Asset
    percent_utilization: float

    def to_tuple(self):
        return (
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
