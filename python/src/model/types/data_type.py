from enum import Enum


class DataItem:
    def __init__(self, di: int, name: str, data_format: str, value: float = 0, unit: str = '', timestamp: int = 0):
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
