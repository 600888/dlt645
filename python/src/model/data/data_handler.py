from typing import Any, Optional, Union

from ...model.data.define.energy_def import DIMap
from ...model.types.data_type import DataItem, DataFormat
from ...model.log import log


# 模拟定义 DIMap 和数据格式常量


def get_data_item(di: int) -> Optional[DataItem]:
    """根据 di 获取数据项"""
    item = DIMap.get(di)
    if item is None:
        log.info(f"未通过di {hex(di)} 找到映射")
        return None
    return item


def set_data_item(di: int, data: Any) -> bool:
    """设置指定 di 的数据项"""
    if data is None:
        log.info("data is nil")
        return False
    if di in DIMap:
        DIMap[di].value = data
        log.info(f"设置数据项 {hex(di)} 成功, 值 {DIMap[di]}")
        return True
    return False


def is_value_valid(data_format: str, value: Union[int, float]) -> bool:
    """检查值是否符合指定的数据格式"""
    try:
        value = float(value)
    except (ValueError, TypeError):
        return False
    if data_format == DataFormat.XXXXXX_XX.value:
        return -799999.99 <= value <= 799999.99
    elif data_format == DataFormat.XXXX_XX.value:
        return -7999.99 <= value <= 7999.99
    elif data_format == DataFormat.XXX_XXX.value:
        return -799.999 <= value <= 799.999
    elif data_format == DataFormat.XX_XXXX.value:
        return -79.9999 <= value <= 79.9999
    return True
