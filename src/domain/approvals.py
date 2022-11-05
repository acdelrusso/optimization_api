from abc import ABC, abstractmethod
from .models import Sku, Asset
from collections import UserDict


class ApprovalSchema(ABC, UserDict):
    @abstractmethod
    def get_approval(self, sku: Sku, asset: Asset) -> bool:
        pass


class VFNApprovals(ApprovalSchema):
    def __init__(self, data):
        super().__init__(data)

    def get_approval(self, sku: Sku, asset: Asset):
        try:
            start, stop = self.data.get(
                (asset.name, sku.region, sku.image, sku.product, sku.market)
            )
        except (KeyError, TypeError):
            try:
                start, stop = self.data.get(
                    (asset.name, sku.region, sku.image, sku.product, "All")
                )
            except (KeyError, TypeError):
                try:
                    start, stop = self.data.get(
                        (asset.name, "All", sku.image, sku.product, "All")
                    )
                except (KeyError, TypeError):
                    return False
        return sku.date <= stop and sku.date >= start


class VpackApprovals(ApprovalSchema):
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
        return sku.date <= stop and sku.date >= start
