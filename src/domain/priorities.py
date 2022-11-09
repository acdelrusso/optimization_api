from abc import ABC, abstractmethod
from .models import Sku, Asset
from collections import UserDict
from .approvals import ApprovalSchema

BIG_M = -10


class PrioritizationSchema(UserDict, ABC):
    def __init__(self, data):
        super().__init__(data)

    @abstractmethod
    def get_priority(self, sku: Sku, asset: Asset) -> float:
        pass


class VariableCosts(PrioritizationSchema):
    def __init__(self, data: dict):
        super().__init__(data)

    def get_priority(self, sku: Sku, asset: Asset):
        if self.data.get((asset.name, sku.date.year, sku.product)) is None:
            return 10 - self.data.get((asset.name, "All", sku.product), 9)
        return 10 - self.data.get((asset.name, sku.date.year, sku.product))


class GeneralPriorities(PrioritizationSchema):
    def __init__(self, data: dict):
        super().__init__(data)

    def get_priority(self, sku: Sku, asset: Asset):
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


class PriorityProvider:
    def __init__(
        self,
        prioritization_scheme: PrioritizationSchema,
        approvals: ApprovalSchema,
    ) -> None:
        self.prioritization_scheme = prioritization_scheme
        self.approvals = approvals

    def get_priority(self, sku: Sku, asset: Asset):
        if self.approvals.get_approval(sku, asset):
            return self.prioritization_scheme.get_priority(sku, asset)
        return BIG_M

    def update(self, data: dict):
        self.prioritization_scheme.update(data)
