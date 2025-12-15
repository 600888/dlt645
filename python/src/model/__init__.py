# 初始化数据类型
import os

from ..common.env import conf_path
from ..model.data.define.demand_def import init_demand_def
from ..model.data.define.energy_def import init_energy_def
from ..model.data.define.variable_def import init_variable_def
from ..model.data.define.parameter_def import init_parameter_def
from ..model.data.define.event_record_def import init_event_record_def
from ..model.types.data_type import init_data_type_from_json

EnergyTypes = []
DemandTypes = []
VariableTypes = []
ParaMeterTypes = []
EventRecordTypes = []


def init():
    global EnergyTypes, DemandTypes, VariableTypes, ParaMeterTypes, EventRecordTypes
    EnergyTypes = init_data_type_from_json(os.path.join(conf_path, "energy_types.json"))
    DemandTypes = init_data_type_from_json(os.path.join(conf_path, "demand_types.json"))
    VariableTypes = init_data_type_from_json(
        os.path.join(conf_path, "variable_types.json")
    )
    ParaMeterTypes = init_data_type_from_json(
        os.path.join(conf_path, "parameter_types.json")
    )
    EventRecordTypes = init_data_type_from_json(
        os.path.join(conf_path, "event_record_types.json")
    )

    init_energy_def(EnergyTypes)
    init_demand_def(DemandTypes)
    init_variable_def(VariableTypes)
    init_parameter_def(ParaMeterTypes)
    init_event_record_def(EventRecordTypes)


# 执行初始化
init()
