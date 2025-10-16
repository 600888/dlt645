from typing import List

from ....model.data.define.energy_def import DIMap
from ....model.types.data_type import DataItem


def init_variable_def(VariableTypes: List[DataItem]):
    for date_type in VariableTypes:
        DIMap[date_type.di] = DataItem(
            di=date_type.di,
            name=date_type.name,
            data_format=date_type.data_format,
            unit=date_type.unit,
        )
