# 初始化数据类型
import os

from ..common.env import conf_path
from ..model.data.define.demand_def import init_demand_def
from ..model.data.define.energy_def import init_energy_def
from ..model.data.define.variable_def import init_variable_def
from ..model.types.dlt645_type import initDataTypeFromJson

EnergyTypes = []
DemandTypes = []
VariableTypes = []


def init():
    global EnergyTypes
    EnergyTypes = initDataTypeFromJson(os.path.join(conf_path, 'energy_types.json'))
    DemandTypes = initDataTypeFromJson(os.path.join(conf_path, 'demand_types.json'))
    VariableTypes = initDataTypeFromJson(os.path.join(conf_path, 'variable_types.json'))

    init_energy_def(EnergyTypes)
    init_demand_def(DemandTypes)
    init_variable_def(VariableTypes)


# 执行初始化
init()
