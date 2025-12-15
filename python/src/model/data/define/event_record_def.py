from typing import List

from . import DIMap
from ....model.types.data_type import DataItem
from ....model.types.dlt645_type import EventRecord
from ....common.transform import pad_with_zeros


def init_event_record_def(EventRecordTypes: List[DataItem]):
    for data_type in EventRecordTypes:
        if data_type.data_format.find(",") == -1:
            value = EventRecord(
                data_type.di, pad_with_zeros(len(data_type.data_format))
            )
        else:
            value = EventRecord(
                data_type.di,
                (
                    pad_with_zeros(len(data_type.data_format.split(",")[0])),
                    pad_with_zeros(len(data_type.data_format.split(",")[1])),
                ),
            )

        if data_type.di not in DIMap:
            DIMap[data_type.di] = []
        data_item = DataItem(
            di=data_type.di,
            name=data_type.name,
            data_format=data_type.data_format,
            value=value,
            unit=data_type.unit,
        )
        DIMap[data_type.di].append(data_item)
