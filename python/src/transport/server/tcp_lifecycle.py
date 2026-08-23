"""TCP 服务端生命周期事件的数据结构。"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Literal, Optional

from ...protocol.frame import Frame


class TcpDisconnectReason(str, Enum):
    """TCP 连接结束原因。"""

    CLIENT_EOF = "client_eof"
    SERVER_STOPPED = "server_stopped"
    CONNECTION_ERROR = "connection_error"
    HANDLER_ERROR = "handler_error"
    CANCELLED = "cancelled"


@dataclass
class TcpConnectionContext:
    """一条 TCP 连接在整个生命周期内共享的可变上下文。

    时间字段是 Unix 时间戳（秒）。``duration`` 使用单调时钟计算，不受系统
    时间校准影响。上层可以保存同一个上下文对象来展示实时状态和累计统计。
    """

    peername: Any
    sockname: Any
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    disconnected_at: Optional[float] = None
    bytes_received: int = 0
    bytes_sent: int = 0
    messages_received: int = 0
    messages_sent: int = 0
    disconnect_reason: Optional[TcpDisconnectReason] = None
    disconnect_error: Optional[BaseException] = field(default=None, repr=False)
    _connected_monotonic: float = field(default_factory=time.monotonic, repr=False)
    _disconnected_monotonic: Optional[float] = field(default=None, repr=False)

    @property
    def status(self) -> Literal["connected", "disconnected"]:
        """返回当前连接状态。"""
        return "disconnected" if self.disconnected_at is not None else "connected"

    @property
    def duration(self) -> float:
        """返回当前或最终连接时长（秒）。"""
        ended_at = self._disconnected_monotonic
        if ended_at is None:
            ended_at = time.monotonic()
        return max(0.0, ended_at - self._connected_monotonic)

    @property
    def peer_host(self) -> Optional[str]:
        """尽可能从 ``peername`` 中提取客户端 IP/主机名。"""
        if isinstance(self.peername, tuple) and self.peername:
            return str(self.peername[0])
        return None

    @property
    def peer_port(self) -> Optional[int]:
        """尽可能从 ``peername`` 中提取客户端端口。"""
        if (
            isinstance(self.peername, tuple)
            and len(self.peername) >= 2
            and isinstance(self.peername[1], int)
        ):
            return self.peername[1]
        return None


@dataclass(frozen=True)
class TcpActivity:
    """一次成功接收或发送的完整 DL/T 645 报文。"""

    direction: Literal["RX", "TX"]
    data: bytes
    timestamp: float
    frame: Optional[Frame] = None


TcpConnectCallback = Callable[[TcpConnectionContext], Any]
TcpActivityCallback = Callable[[TcpConnectionContext, TcpActivity], Any]
TcpDisconnectCallback = Callable[[TcpConnectionContext], Any]
