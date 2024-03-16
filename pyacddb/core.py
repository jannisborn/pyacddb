import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import pandas as pd

from pyacddb.metadata import DEFAULT_FIELDS
from pyacddb.utils import strip


def field_items_from_root(
    root, item: str = "Keyword", fields: List[str] = None
) -> List[Dict[str, Optional[str]]]:
    if fields is None:
        fields = []
    results = [
        {field: field_from_item(res, field) for field in fields}
        for res in root.findall(f".//{item}")
    ]
    return results


def field_from_item(item: str, field: str):
    return strip(item.find(field).text) if item.find(field) is not None else None


def extract_keywords(path: str, fields: List[str] = DEFAULT_FIELDS):

    tree = ET.parse(path)
    root = tree.getroot()
    assets = []
    unique_tags = set()

    asset_items = field_items_from_root(root, "Asset", fields)

    for asset_dict in asset_items:
        # Extract asset categories directly within this loop
        asset_categories = [
            strip(ac.text)
            for ac in root.findall(
                f".//Asset[Name='{asset_dict['Name']}']//AssetCategory"
            )
        ]
        tags = [a.split("\\")[-1] for a in asset_categories]
        unique_tags.update(tags)

        # Update the asset dictionary with categories and tags
        asset_dict.update({"AssetCategories": asset_categories, "Tags": tags})
        assets.append(asset_dict)

    assets_df = pd.DataFrame(assets)
    # For each unique tag, create a new column in the DataFrame
    for tag in unique_tags:
        assets_df[tag] = assets_df["Tags"].apply(lambda x: tag in x)
    return assets_df
