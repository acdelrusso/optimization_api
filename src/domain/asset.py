import dataclasses
from pydantic import BaseModel


@dataclasses.dataclass(frozen=True, eq=False)
class Asset(BaseModel):
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
