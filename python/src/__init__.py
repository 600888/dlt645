"""DLT645协议Python实现库

这个库提供了DLT645通信协议的完整实现，包括：
- TCP和RTU通信方式
- 客户端和服务端功能
- 电能表数据读写操作
- 电能量、最大需量、变量数据类型支持
- 实时报文捕获功能
"""

__version__ = "1.0.0"
__author__ = "Chen Dongyu"
__email__ = "1755696012@qq.com"

# 导入主要的服务类
from .service.serversvc.server_service import (
    MeterServerService,
)
from .service.clientsvc.client_service import MeterClientService

# 导入协议相关
from .protocol.protocol import DLT645Protocol
from .model.types.dlt645_type import CtrlCode, Demand
from .model.types.data_type import DataItem, DataFormat

# 导入传输层
from .transport.server.tcp_server import TcpServer
from .transport.server.rtu_server import RtuServer
from .transport.client.tcp_client import TcpClient
from .transport.client.rtu_client import RtuClient

# 导入报文捕获模块
from .common.message_types import MessageRecord, MessagePair
from .common.message_capture import MessageCapture, MessageQueue

# 导出所有公共接口
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    
    # 服务类
    "MeterServerService",
    "MeterClientService",
    
    # 协议类
    "DLT645Protocol",
    
    # 数据类型
    "CtrlCode",
    "Demand",
    "DataItem",
    "DataFormat",
    
    # 传输层
    "TcpServer",
    "RtuServer",
    "TcpClient",
    "RtuClient",
    
    # 报文捕获
    "MessageRecord",
    "MessagePair",
    "MessageCapture",
    "MessageQueue",
]