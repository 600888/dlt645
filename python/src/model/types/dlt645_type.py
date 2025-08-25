import json
from enum import IntEnum
from time import time
from src.model.log import log


# 模拟 DICategory 枚举
class DICategory(IntEnum):
    CategoryEnergy = 0  # 电能
    CategoryDemand = 1  # 需量
    CategoryVariable = 2  # 变量
    CategoryEvent = 3  # 事件记录
    CategoryParameter = 4  # 参变量
    CategoryFreeze = 5  # 冻结量
    CategoryLoad = 6  # 负荷纪录


class CtrlCode(IntEnum):
    BroadcastTimeSync = 0x08  # 广播校时
    ReadData = 0x11  # 读数据
    ReadAddress = 0x13  # 读通讯地址
    WriteData = 0x14  # 写数据
    WriteAddress = 0x15  # 写通讯地址
    FreezeCmd = 0x16  # 冻结命令
    ChangeBaudRate = 0x17  # 修改通信速率
    ChangePassword = 0x18  # 改变密码


class Demand:
    def __init__(self, value: float, time: time):
        self.value = value
        self.time = time


# 模拟 Uint32FromString 类型和其反序列化功能
class Uint32FromString(int):
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


class DataType:
    def __init__(self, Di="", Name="", Unit="", DataFormat=""):
        self.di = Uint32FromString.from_json(Di)
        self.name = Name
        self.unit = Unit
        self.data_format = DataFormat

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


def initDataTypeFromJson(file_path: str):
    try:
        # 读取 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 解析 JSON 到列表
        data_types = [DataType.from_dict(item) for item in json_data]
        log.info(f"初始化 {file_path} 完成，共加载 {len(data_types)} 种数据类型")
        return data_types
    except FileNotFoundError as e:
        log.error(f"读取文件失败: {e}")
        raise
    except json.JSONDecodeError as e:
        log.error(f"解析 JSON 失败: {e}")
        raise
