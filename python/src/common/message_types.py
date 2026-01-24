"""报文捕获数据类型模块。

本模块定义了用于实时报文捕获的数据结构：
- MessageRecord: 单条报文记录
- MessagePair: TX/RX配对记录
"""

import uuid
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .transform import bytes_to_spaced_hex


@dataclass
class MessageRecord:
    """单条报文记录。

    用于存储发送或接收的单条报文数据。

    :ivar id: 唯一标识符 (UUID)
    :ivar direction: 报文方向，"TX"（发送）或 "RX"（接收）
    :ivar data: 原始报文数据
    :ivar timestamp: 时间戳（秒，带小数部分）
    :ivar hex_string: 十六进制字符串表示
    :ivar pair_id: 配对的报文ID，用于TX/RX关联
    """

    direction: str
    data: bytes
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    hex_string: str = field(default="")
    pair_id: Optional[str] = field(default=None)

    def __post_init__(self):
        """初始化后处理，自动生成hex_string。"""
        if not self.hex_string and self.data:
            self.hex_string = bytes_to_spaced_hex(self.data)

    def __repr__(self) -> str:
        """自定义字符串表示，显示格式化时间。"""
        return (
            f"MessageRecord(direction='{self.direction}', "
            f"time='{self.formatted_time}', "
            f"hex='{self.hex_string}')"
        )

    @property
    def formatted_time(self) -> str:
        """获取格式化的时间字符串（年-月-日 时:分:秒.毫秒）。

        :return: 格式化的时间字符串
        :rtype: str
        """
        dt = datetime.fromtimestamp(self.timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # 截取到毫秒

    def to_dict(self) -> dict:
        """转换为字典格式。

        :return: 包含所有字段的字典
        :rtype: dict
        """
        return {
            "id": self.id,
            "direction": self.direction,
            "data": self.data.hex() if self.data else "",
            "timestamp": self.timestamp,
            "time": self.formatted_time,
            "hex_string": self.hex_string,
            "pair_id": self.pair_id,
        }


@dataclass
class MessagePair:
    """TX/RX配对记录。

    用于将发送报文和接收报文配对，便于分析请求-响应对。

    :ivar id: 配对ID
    :ivar tx: 发送报文记录
    :ivar rx: 接收报文记录
    :ivar round_trip_time: 往返时间（秒）
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tx: Optional[MessageRecord] = field(default=None)
    rx: Optional[MessageRecord] = field(default=None)
    round_trip_time: Optional[float] = field(default=None)

    def __post_init__(self):
        """初始化后处理，自动计算往返时间。"""
        self._update_round_trip_time()

    def __repr__(self) -> str:
        """自定义字符串表示，按时间顺序显示（先收到的在前）。"""
        rtt_ms = f"{abs(self.round_trip_time) * 1000:.2f}ms" if self.round_trip_time else "N/A"
        tx_hex = self.tx.hex_string if self.tx else "N/A"
        rx_hex = self.rx.hex_string if self.rx else "N/A"
        
        # 判断是服务端模式（RX先于TX）还是客户端模式（TX先于RX）
        if self.tx and self.rx and self.rx.timestamp < self.tx.timestamp:
            # 服务端模式：先RX（请求），后TX（响应）
            return (
                f"MessagePair(\n"
                f"  RX[{self.rx_time}]: {rx_hex}\n"
                f"  TX[{self.tx_time}]: {tx_hex}\n"
                f"  RTT: {rtt_ms}\n"
                f")"
            )
        else:
            # 客户端模式：先TX（请求），后RX（响应）
            return (
                f"MessagePair(\n"
                f"  TX[{self.tx_time}]: {tx_hex}\n"
                f"  RX[{self.rx_time}]: {rx_hex}\n"
                f"  RTT: {rtt_ms}\n"
                f")"
            )

    def set_tx(self, record: MessageRecord) -> None:
        """设置发送报文。

        :param record: 发送报文记录
        :type record: MessageRecord
        """
        self.tx = record
        record.pair_id = self.id
        self._update_round_trip_time()

    def set_rx(self, record: MessageRecord) -> None:
        """设置接收报文。

        :param record: 接收报文记录
        :type record: MessageRecord
        """
        self.rx = record
        record.pair_id = self.id
        self._update_round_trip_time()

    def _update_round_trip_time(self) -> None:
        """更新往返时间（始终为正值）。"""
        if self.tx is not None and self.rx is not None:
            self.round_trip_time = abs(self.tx.timestamp - self.rx.timestamp)

    def is_complete(self) -> bool:
        """检查配对是否完整（有TX和RX）。

        :return: 配对是否完整
        :rtype: bool
        """
        return self.tx is not None and self.rx is not None

    @property
    def tx_time(self) -> Optional[str]:
        """获取发送报文的格式化时间。

        :return: 格式化的发送时间，如果没有TX则返回None
        :rtype: Optional[str]
        """
        return self.tx.formatted_time if self.tx else None

    @property
    def rx_time(self) -> Optional[str]:
        """获取接收报文的格式化时间。

        :return: 格式化的接收时间，如果没有RX则返回None
        :rtype: Optional[str]
        """
        return self.rx.formatted_time if self.rx else None

    def to_dict(self) -> dict:
        """转换为字典格式。

        :return: 包含所有字段的字典
        :rtype: dict
        """
        return {
            "id": self.id,
            "tx": self.tx.to_dict() if self.tx else None,
            "rx": self.rx.to_dict() if self.rx else None,
            "tx_time": self.tx_time,
            "rx_time": self.rx_time,
            "round_trip_time": self.round_trip_time,
            "is_complete": self.is_complete(),
        }
