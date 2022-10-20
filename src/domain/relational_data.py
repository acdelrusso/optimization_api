from collections import UserDict
from .sku import Sku
from .asset import Asset


class RunRates(UserDict):
    def __init__(self, data):
        super().__init__(data)

    def get_utilization(self, sku: Sku, asset: Asset, scale: float = 1.0):
        try:
            rate, cuco = self.__getitem__((asset.name, sku.image, sku.config))
            return scale * (
                ((sku.doses / rate) + (cuco * sku.batches)) / asset.capacities[sku.year]
            )
        except (ZeroDivisionError, KeyError):
            return 1000000


class Approvals(UserDict):
    def __init__(self, data):
        super().__init__(data)

    def get_approval(self, sku: Sku, asset: Asset):
        try:
            start, stop = self.data.get(
                (asset.name, sku.region, sku.image, sku.config, sku.product)
            )
        except (KeyError, TypeError):
            try:
                start, stop = self.data.get(
                    (asset.name, sku.region, sku.image, sku.config, "All")
                )
            except (KeyError, TypeError):
                return False
        return sku.year <= stop and sku.year >= start


class Priorities(UserDict):
    def __init__(self, data: dict, approvals: Approvals):
        self.approvals = approvals
        super().__init__(data)

    def get_priority(self, sku: Sku, asset: Asset):
        if self.approvals.get_approval(sku, asset):
            return (
                10
                - (
                    self.data.get(asset.name)
                    + self.data.get((asset.name, sku.region), 5)
                    + self.data.get((asset.name, sku.product), 5)
                    + self.data.get((asset.name, sku.config), 5)
                )
                / 10
            )
        return -10
