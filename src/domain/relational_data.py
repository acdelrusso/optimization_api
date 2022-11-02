from collections import UserDict
from .models import Sku, Asset



class RunRates(UserDict):
    def __init__(self, data):
        super().__init__(data)

    def get_utilization(self, sku: Sku, asset: Asset, scale: float = 1.0):
        try:
            rate, cuco = self.__getitem__((asset.name, sku.image, sku.config))
            return scale * (
                ((sku.doses / rate) + (cuco * sku.batches))
                / asset.capacities[sku.date.year]
            )
        except (ZeroDivisionError, KeyError):
            return 1000000




