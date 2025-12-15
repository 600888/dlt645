from typing import List

from . import DIMap
from ....model.types.data_type import DataItem


def init_variable_def(VariableTypes: List[DataItem]):
    for data_type in VariableTypes:
        DIMap[data_type.di] = DataItem(
            di=data_type.di,
            name=data_type.name,
            data_format=data_type.data_format,
            unit=data_type.unit,
        )
