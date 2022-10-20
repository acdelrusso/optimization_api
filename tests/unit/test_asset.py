from src.domain.asset import Asset


def test_asset_init(asset_values):
    asset = Asset(**asset_values)

    for attr in asset_values:
        assert getattr(asset, attr) == asset_values[attr]

def test_built_asset_from_record(asset_values):
    record = {
        "Asset": "Haarlem-V11",
        "Site_Code": "1014",
        "Asset_Key": "W40V11_1014_008",
        "Type": "Internal",
        "Image": "SYRINGE",
        2022: 5760,
        2023: 5760,
        2024: 5760
    }
    
    asset = Asset.from_record(record)
    
    for attr in asset_values:
        assert getattr(asset, attr) == asset_values[attr]
    
    