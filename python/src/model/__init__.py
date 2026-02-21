# 初始化数据类型

from ..config.energy_types import ENERGY_TYPES
from ..config.demand_types import DEMAND_TYPES
from ..config.variable_types import VARIABLE_TYPES
from ..config.parameter_types import PARAMETER_TYPES
from ..config.event_record_types import EVENT_RECORD_TYPES
from ..model.data.define.demand_def import init_demand_def
from ..model.data.define.energy_def import init_energy_def
from ..model.data.define.variable_def import init_variable_def
from ..model.data.define.parameter_def import init_parameter_def
from ..model.data.define.event_record_def import init_event_record_def
from ..model.types.data_type import init_data_type_from_list

EnergyTypes = []
DemandTypes = []
VariableTypes = []
ParaMeterTypes = []
EventRecordTypes = []


def init():
    global EnergyTypes, DemandTypes, VariableTypes, ParaMeterTypes, EventRecordTypes
    EnergyTypes = init_data_type_from_list(ENERGY_TYPES)
    DemandTypes = init_data_type_from_list(DEMAND_TYPES)
    VariableTypes = init_data_type_from_list(VARIABLE_TYPES)
    ParaMeterTypes = init_data_type_from_list(PARAMETER_TYPES)
    EventRecordTypes = init_data_type_from_list(EVENT_RECORD_TYPES)

    init_energy_def(EnergyTypes)
    init_demand_def(DemandTypes)
    init_variable_def(VariableTypes)
    init_parameter_def(ParaMeterTypes)
    init_event_record_def(EventRecordTypes)


# 执行初始化
init()
