from typing import List

from . import DIMap
from ....model.types.data_type import DataItem
from ....common.transform import pad_with_zeros


def init_parameter_def(ParaMeterTypes: List[DataItem]):
    """初始化参变量定义
    
    Args:
        ParaMeterTypes: 参变量类型列表，包含参变量类型
    """
    for data_type in ParaMeterTypes:
        di = int(data_type.di)
        # 时段表数据
        if 0x04010000 <= di <= 0x04020008:
            if data_type.di not in DIMap:
                DIMap[data_type.di] = []
            data_item = DataItem(
                di=data_type.di,
                name=data_type.name,
                data_format=data_type.data_format,
                value=pad_with_zeros(len(data_type.data_format)),
                unit=data_type.unit,
            )
            DIMap[data_type.di].append(data_item)
        else:
            DIMap[data_type.di] = DataItem(
                di=data_type.di,
                name=data_type.name,
                data_format=data_type.data_format,
                value=pad_with_zeros(len(data_type.data_format)),
                unit=data_type.unit,
            )
