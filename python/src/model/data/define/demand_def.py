from typing import List

from src.model.data.define.energy_def import DIMap
from src.model.types.data_type import DataItem, DataFormat

# 需求DI列表
demand_di_list = [
    0x01150000,
    0x01160000,
    0x01170000,
    0x01180000,
    0x01190000,
    0x011A0000,
    0x011B0000,
    0x011C0000,
    0x011D0000,
    0x011E0000,
    0x01290000,
    0x012A0000,
    0x012B0000,
    0x012C0000,
    0x012D0000,
    0x012E0000,
    0x012F0000,
    0x01300000,
    0x01310000,
    0x01320000,
    0x013D0000,
    0x013E0000,
    0x013F0000,
    0x01400000,
    0x01410000,
    0x01420000,
    0x01430000,
    0x01440000,
    0x01450000,
    0x01460000,
]


def init_demand_def(demand_types: List[DataItem]):
    """
    初始化需求定义
    """
    di3 = 0  # 数据类型
    di2 = 0  # 电能类型
    di1 = 0  # 同一类型电能里的不同项
    di0 = 0  # 结算日

    for i in range(64):
        for j in range(13):
            if j == 0:
                name_prefix = "（当前）"
            else:
                name_prefix = f"（上{j}结算日）"

            # 正向有功需量
            key = (di3 + 1) << 24 | (di2 + 1) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[i].unit
            )

            # 反向有功需量
            key = (di3 + 1) << 24 | (di2 + 2) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 + i].unit
            )

            # 组合无功1需量
            key = (di3 + 1) << 24 | (di2 + 3) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 2 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 2 + i].unit
            )

            # 组合无功2需量
            key = (di3 + 1) << 24 | (di2 + 4) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 3 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 3 + i].unit
            )

            # 第一象限无功费率最大需量
            key = (di3 + 1) << 24 | (di2 + 5) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 4 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 4 + i].unit
            )

            # 第二象限无功费率最大需量
            key = (di3 + 1) << 24 | (di2 + 6) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 5 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 5 + i].unit
            )

            # 第三象限无功费率最大需量
            key = (di3 + 1) << 24 | (di2 + 7) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 6 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 6 + i].unit
            )

            # 第四象限无功费率最大需量
            key = (di3 + 1) << 24 | (di2 + 8) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 7 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 7 + i].unit
            )

            # 正向视在最大需量
            key = (di3 + 1) << 24 | (di2 + 9) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 8 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 8 + i].unit
            )

            # 反向视在最大需量
            key = (di3 + 1) << 24 | (di2 + 10) << 16 | (di1 + i) << 8 | (di0 + j)
            DIMap[key] = DataItem(
                di=key,
                name=name_prefix + demand_types[64 * 9 + i].name,
                data_format=DataFormat.XX_XXXX.value,
                unit=demand_types[64 * 9 + i].unit
            )

            # 最后几个数据特殊处理
            for k in range(len(demand_di_list)):
                key = demand_di_list[k]
                DIMap[key] = DataItem(
                    di=key,
                    name=name_prefix + demand_types[64 * 10 + k].name,
                    data_format=DataFormat.XX_XXXX.value,
                    unit=demand_types[64 * 10 + k].unit
                )
