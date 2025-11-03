from typing import List

from ....model.data.define.energy_def import DIMap
from ....model.types.data_type import DataItem

# 根据长度补0
def pad_with_zeros(length: int) -> str:
    return "0" * length

def init_parameter_def(ParaMeterTypes: List[DataItem]):
    for date_type in ParaMeterTypes:
        # 时段表数据
        di = int(date_type.di)
        if 0x04010000 <= di <=0x04020008:
            schedule_list = []
            for i in range(0, 14):
                schedule_list.append(pad_with_zeros(len(date_type.data_format)))
            value = schedule_list
        else:
            value=pad_with_zeros(len(date_type.data_format))
            
        DIMap[date_type.di] = DataItem(
            di=date_type.di,
            name=date_type.name,
            data_format=date_type.data_format,
            value=value,
            unit=date_type.unit,
        )
