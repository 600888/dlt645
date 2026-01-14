from ast import List
from enum import Enum
from typing import Union
import datetime
import json
from ...model.log import log


class DataItem:
    """
    数据项实体类，表示一个具体的数据项。

    :ivar di: 数据标识 (DI)，4 字节。
    :ivar name: 数据项名称。
    :ivar data_format: 数据格式字符串（如 "XXXXXX.XX"）。
    :ivar value: 数据值。
    :ivar unit: 数据单位。
    :ivar update_time: 最后更新时间戳。
    """

    def __init__(
        self,
        di: int,
        name: str,
        data_format: str,
        value: Union[str, float, List] = 0,
        unit: str = "",
        update_time: datetime.datetime = datetime.datetime.now(),
    ):
        """
        初始化 DataItem 实例。

        :param di: 数据标识 (DI)。
        :type di: int
        :param name: 数据项名称。
        :type name: str
        :param data_format: 定义数据结构的格式。
        :type data_format: str
        :param value: 数据项的实际值，默认为 0。
        :type value: Union[str, float, List], 可选
        :param unit: 单位字符串（如 "kWh"），默认为空字符串。
        :type unit: str, 可选
        :param update_time: 数据更新的时间戳，默认为当前时间。
        :type update_time: datetime.datetime, 可选
        """
        self.di = di
        self.name = name
        self.data_format = data_format
        self.value = value
        self.unit = unit
        self.update_time = update_time

    def __repr__(self):
        """
        返回 DataItem 的字符串表示。

        :return: 字符串表示。
        :rtype: str
        """
        return (
            f"DataItem(name={self.name}, di={format(self.di, '#x')}, value={self.value}, "
            f"unit={self.unit},data_format={self.data_format}, timestamp={datetime.datetime.strftime(self.update_time, '%Y-%m-%d %H:%M:%S')})"
        )


class DataType:
    """
    数据类型配置类，通常从 JSON 加载。

    :ivar di: 数据标识 (DI)，整数形式。
    :ivar name: 数据类型名称。
    :ivar unit: 计量单位。
    :ivar data_format: 格式字符串定义。
    """

    def __init__(self, Di="", Name="", Unit="", DataFormat=""):
        """
        初始化 DataType 实例。

        :param Di: 数据标识字符串（十六进制），默认为空字符串。
        :type Di: str, 可选
        :param Name: 数据类型名称，默认为空字符串。
        :type Name: str, 可选
        :param Unit: 计量单位，默认为空字符串。
        :type Unit: str, 可选
        :param DataFormat: 格式字符串，默认为空字符串。
        :type DataFormat: str, 可选
        """
        self.di = uint32_from_string.from_json(Di)
        self.name = Name
        self.unit = Unit
        self.data_format = DataFormat

    @classmethod
    def from_dict(cls, data):
        """
        从字典创建 DataType 实例。

        :param data: 包含 'Di', 'Name', 'Unit', 'DataFormat' 的字典。
        :type data: dict
        :return: DataType 实例。
        :rtype: DataType
        """
        return cls(**data)


class uint32_from_string(int):
    """
    自定义整数类型，用于处理从 JSON 字符串（包括十六进制）解析 uint32。
    """

    @classmethod
    def from_json(cls, data):
        """
        将输入数据解析为 uint32 整数。

        处理以下情况：
        - 空字符串 -> 0
        - 十六进制字符串（带或不带 0x 前缀）
        - 普通整数

        :param data: 待解析的输入数据。
        :type data: Union[str, int]
        :return: 解析后的整数值。
        :rtype: uint32_from_string
        :raises ValueError: 如果转换失败。
        """
        if data == "":
            return cls(0)
        if isinstance(data, str):
            try:
                return cls(int(data, 16))
            except ValueError as e:
                raise ValueError(f"无法转换为 uint32: {e}")
        return cls(data)


def init_data_type_from_json(file_path: str):
    """
    从 JSON 文件初始化 DataType 对象列表。

    读取指定的 JSON 文件，解析后返回 DataType 实例列表。

    :param file_path: JSON 配置文件的路径。
    :type file_path: str
    :return: 初始化后的 DataType 对象列表。
    :rtype: list[DataType]
    :raises FileNotFoundError: 如果 JSON 文件不存在。
    :raises json.JSONDecodeError: 如果 JSON 文件格式无效。
    """
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
    """
    表示各种数据格式模板的枚举。

    定义说明：
    - X: 十进制数字
    - Y: 年
    - M: 月
    - D: 日
    - W: 星期
    - h: 时
    - m: 分
    - s: 秒
    - N: 数字（通用）
    """

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
