from typing import Any, Optional, Union

from ...model.data.define.energy_def import DIMap
from ...model.types.data_type import DataItem, DataFormat
from ...model.types.dlt645_type import Demand
from ...model.log import log


# 模拟定义 DIMap 和数据格式常量


def get_data_item(di: int) -> Optional[DataItem]:
    """根据 di 获取数据项"""
    item = DIMap.get(di)
    if item is None:
        log.error(f"未通过di {hex(di)} 找到映射")
        return None
    return item


def set_data_item(di: int, data: Union[int, float, str, Demand, list]) -> bool:
    """设置指定 di 的数据项"""
    if di in DIMap:
        item = DIMap[di]
        if isinstance(data, Demand):
            if not is_value_valid(item.data_format, data.value):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
        elif 0x04010000 <= di <=0x04020008: # 时段表数据
            for item_data in data:
                if not is_value_valid(item.data_format, item_data):
                    log.error(f"值 {item_data} 不符合数据格式: {item.data_format}")
                    return False
        else:
            if not is_value_valid(item.data_format, data):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
        item.value = data
        log.debug(f"设置数据项 {hex(di)} 成功, 值 {item}")
        return True
    return False


def is_value_valid(data_format: str, value: Union[int, float, str]) -> bool:
    """检查值是否符合指定的数据格式"""
    if data_format == DataFormat.XXXXXX_XX.value:
        return -799999.99 <= value <= 799999.99
    elif data_format == DataFormat.XXXX_XX.value:
        return -7999.99 <= value <= 7999.99
    elif data_format == DataFormat.XXX_XXX.value:
        return -799.999 <= value <= 799.999
    elif data_format == DataFormat.XX_XXXX.value:
        return -79.9999 <= value <= 79.9999
    else:
        if isinstance(value, str) and len(value)==len(data_format):
            return True
        else:
            return False
