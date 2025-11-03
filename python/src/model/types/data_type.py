from ast import List
from enum import Enum
from typing import Union

class DataItem:
    def __init__(self, di: int, name: str, data_format: str, value: Union[str, float, List] = 0, unit: str = '', timestamp: int = 0):
        self.di = di
        self.name = name
        self.data_format = data_format
        self.value = value
        self.unit = unit
        self.timestamp = timestamp

    def __repr__(self):
        return (f"DataItem(name={self.name}, di={format(self.di, '#x')}, value={self.value}, "
                f"unit={self.unit},data_format={self.data_format}, timestamp={self.timestamp})")


class DataFormat(Enum):
    XXXXXXXX = "XXXXXXXX"
    XXXXXX_XX = "XXXXXX.XX"
    XXXX_XX = "XXXX.XX"
    XXX_XXX = "XXX.XXX"
    XX_XXXX = "XX.XXXX"
    YYMMDDWW = "YYMMDDWW" # 日年月日星期
    hhmmss = "hhmmss" # 时分秒
    YYMMDDhhmm = "YYMMDDhhmm" # 日年月日时分
    NN = "NN"
    NNNN = "NNNN"
    NNNNNNNN = "NNNNNNNN"
