from typing import List

from . import DIMap
from ....model.types.data_type import DataItem


def init_variable_def(VariableTypes: List[DataItem]):
    """初始化变量定义
    
    Args:
        VariableTypes: 变量类型列表，包含变量类型
    """
    for data_type in VariableTypes:
        DIMap[data_type.di] = DataItem(
            di=data_type.di,
            name=data_type.name,
            data_format=data_type.data_format,
            unit=data_type.unit,
        )
