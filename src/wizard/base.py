from abc import ABC

import pandas as pd
from pydantic import BaseModel, ConfigDict


def dataframe_serializer(v: pd.DataFrame) -> list[list]:
    return [[cell for cell in row if not cell.is_empty()] for row in v.values]


class Serializable(BaseModel, ABC):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={pd.DataFrame: dataframe_serializer},
        populate_by_name=True,  # allow setting fields by field name and not just alias
    )
