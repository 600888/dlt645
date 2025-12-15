from ast import List
from enum import Enum
from typing import Union
from datetime import datetime
import json
from ...model.log import log


class DataItem:
    def __init__(
        self,
        di: int,
        name: str,
        data_format: str,
        value: Union[str, float, List] = 0,
        unit: str = "",
        update_time: datetime = datetime.now(),
    ):
        self.di = di
        self.name = name
        self.data_format = data_format
        self.value = value
        self.unit = unit
        self.update_time = update_time

    def __repr__(self):
        return (
            f"DataItem(name={self.name}, di={format(self.di, '#x')}, value={self.value}, "
            f"unit={self.unit},data_format={self.data_format}, timestamp={datetime.strftime(self.update_time, '%Y-%m-%d %H:%M:%S')})"
        )


class DataType:
    def __init__(self, Di="", Name="", Unit="", DataFormat=""):
        self.di = uint32_from_string.from_json(Di)
        self.name = Name
        self.unit = Unit
        self.data_format = DataFormat

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class uint32_from_string(int):
    @classmethod
    def from_json(cls, data):
        if data == "":
            return cls(0)
        if isinstance(data, str):
            try:
                return cls(int(data, 16))
            except ValueError as e:
                raise ValueError(f"无法转换为 uint32: {e}")
        return cls(data)


def init_data_type_from_json(file_path: str):
    try:
        # 读取 JSON 文件
        with open(file_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # 解析 JSON 到列表
        data_types = [DataType.from_dict(item) for item in json_data]
        # log.debug(f"初始化 {file_path} 完成，共加载 {len(data_types)} 种数据类型")
        return data_types
    except FileNotFoundError as e:
        log.error(f"读取文件失败: {e}")
        raise
    except json.JSONDecodeError as e:
        log.error(f"解析 JSON 失败: {e}")
        raise


class DataFormat(Enum):
    XXXXXXXX = "XXXXXXXX"
    XXXXXX_XX = "XXXXXX.XX"
    XXXX_XX = "XXXX.XX"
    XXX_XXX = "XXX.XXX"
    XX_XXXX = "XX.XXXX"
    XXX_X = "XXX.X"
    X_XXX = "X.XXX"
    YYMMDDWW = "YYMMDDWW"  # 日年月日星期
    hhmmss = "hhmmss"  # 时分秒
    YYMMDDhhmm = "YYMMDDhhmm"  # 日年月日时分
    NN = "NN"
    NNNN = "NNNN"
    NNNNNNNN = "NNNNNNNN"
