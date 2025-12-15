from typing import Optional, Union, List

from ...model.types.data_type import DataItem, DataFormat
from ...model.types.dlt645_type import Demand, EventRecord
from ...model.log import log
from .define import DIMap


def get_data_item(di: int) -> Optional[DataItem | List[DataItem]]:
    """根据 di 获取数据项"""
    item = DIMap.get(di)
    if item is None:
        log.error(f"未通过di {hex(di)} 找到映射")
        return None
    return item


def set_data_item(di: int, data: Union[int, float, str, Demand, list, tuple]) -> bool:
    """设置指定 di 的数据项"""
    if di in DIMap:
        item = DIMap[di]
        if isinstance(data, Demand):
            if not is_value_valid(item.data_format, data.value):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        elif 0x03010000 <= di <= 0x03300E0A:  # 事件记录数据
            for data_item, value in zip(item, data):  # data的每一条数据是一个事件记录
                if not is_value_valid(data_item.data_format, value):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value.event = value
        elif 0x04010000 <= di <= 0x04020008:  # 参变量时段表数据
            for data_item, value in zip(item, data):
                if not is_value_valid(data_item.data_format, value):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value = value
        else:
            if not is_value_valid(item.data_format, data):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        log.debug(f"设置数据项 {hex(di)} 成功, 值 {item}")
        return True
    return False


def is_value_valid(data_format: str, value: Union[int, float, str, tuple]) -> bool:
    """检查值是否符合指定的数据格式"""
    if data_format == DataFormat.XXXXXX_XX.value:
        return -799999.99 <= value <= 799999.99
    elif data_format == DataFormat.XXXX_XX.value:
        return -7999.99 <= value <= 7999.99
    elif data_format == DataFormat.XXX_XXX.value:
        return -799.999 <= value <= 799.999
    elif data_format == DataFormat.XX_XXXX.value:
        return -79.9999 <= value <= 79.9999
    elif data_format == DataFormat.XXX_X.value:
        return -799.9 <= value <= 799.9
    elif data_format == DataFormat.X_XXX.value:
        return -0.999 <= value <= 0.999
    else:
        if isinstance(value, str) and len(value) == len(data_format):
            return True
        elif isinstance(value, tuple):
            fmt = data_format.split(",")
            for v, fmt in zip(value, fmt):
                if not is_value_valid(fmt, v):
                    return False
            return True
        else:
            return False
