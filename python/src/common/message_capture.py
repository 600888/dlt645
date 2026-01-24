"""报文捕获管理模块。

本模块实现了实时报文捕获功能：
- MessageQueue: 线程安全的报文队列
- MessageCapture: 报文捕获管理器
"""

import threading
import time
from collections import deque
from typing import List, Dict, Optional

from .message_types import MessageRecord, MessagePair


class MessageQueue:
    """线程安全的报文队列。

    使用deque实现固定大小的循环队列，当队列满时自动丢弃最旧的记录。

    :ivar _queue: 内部队列
    :ivar _lock: 线程锁
    """

    def __init__(self, maxlen: int = 100):
        """初始化报文队列。

        :param maxlen: 队列最大长度，默认100
        :type maxlen: int
        """
        self._queue: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._maxlen = maxlen

    @property
    def maxlen(self) -> int:
        """获取队列最大长度。"""
        return self._maxlen

    def append(self, record) -> None:
        """添加记录到队列。

        :param record: 要添加的记录（MessageRecord或MessagePair）
        """
        with self._lock:
            self._queue.append(record)

    def get_all(self) -> List:
        """获取所有记录。

        :return: 所有记录的列表副本
        :rtype: List
        """
        with self._lock:
            return list(self._queue)

    def get_recent(self, count: int) -> List:
        """获取最近的N条记录。

        :param count: 要获取的记录数量
        :type count: int
        :return: 最近的记录列表
        :rtype: List
        """
        with self._lock:
            if count <= 0 or count >= len(self._queue):
                return list(self._queue)
            return list(self._queue)[-count:]

    def clear(self) -> None:
        """清空队列。"""
        with self._lock:
            self._queue.clear()

    def __len__(self) -> int:
        """获取队列当前长度。"""
        with self._lock:
            return len(self._queue)

    def resize(self, new_maxlen: int) -> None:
        """调整队列大小。

        :param new_maxlen: 新的最大长度
        :type new_maxlen: int
        """
        with self._lock:
            old_items = list(self._queue)
            self._queue = deque(maxlen=new_maxlen)
            self._maxlen = new_maxlen
            # 保留最新的记录
            for item in old_items[-new_maxlen:]:
                self._queue.append(item)


class MessageCapture:
    """报文捕获管理器。

    管理TX和RX报文的捕获、配对和存储。
    默认禁用，需要显式调用enable()启用。

    :ivar _enabled: 是否启用捕获
    :ivar _queue_size: 队列大小
    :ivar _tx_queue: 发送报文队列
    :ivar _rx_queue: 接收报文队列
    :ivar _pairs: 配对队列
    :ivar _pending_pairs: 等待配对的记录（TX等待RX）
    """

    def __init__(self, enabled: bool = False, queue_size: int = 100):
        """初始化报文捕获管理器。

        :param enabled: 是否启用捕获，默认False
        :type enabled: bool
        :param queue_size: 队列大小，默认100
        :type queue_size: int
        """
        self._enabled = enabled
        self._queue_size = queue_size
        self._tx_queue = MessageQueue(queue_size)  # 发送报文
        self._rx_queue = MessageQueue(queue_size)  # 接收报文
        self._pairs = MessageQueue(queue_size)  # 已配对的报文
        self._pending_pairs: Dict[str, MessagePair] = {}    # 待配对的报文
        self._lock = threading.Lock()
        # 待配对超时时间（秒）
        self._pair_timeout = 30.0

    @property
    def enabled(self) -> bool:
        """获取启用状态。"""
        return self._enabled

    @property
    def queue_size(self) -> int:
        """获取队列大小。"""
        return self._queue_size

    def enable(self) -> None:
        """启用报文捕获。"""
        self._enabled = True

    def disable(self) -> None:
        """禁用报文捕获。"""
        self._enabled = False

    def set_queue_size(self, size: int) -> None:
        """设置队列大小。

        :param size: 新的队列大小
        :type size: int
        """
        self._queue_size = size
        self._tx_queue.resize(size)
        self._rx_queue.resize(size)
        self._pairs.resize(size)

    def capture_tx(self, data: bytes) -> Optional[str]:
        """捕获发送报文。

        :param data: 发送的原始数据
        :type data: bytes
        :return: 事务ID，用于后续配对RX
        :rtype: Optional[str]
        """
        if not self._enabled:
            return None

        record = MessageRecord(direction="TX", data=data)
        self._tx_queue.append(record)

        # 创建配对并等待RX
        pair = MessagePair()
        pair.set_tx(record)

        with self._lock:
            self._pending_pairs[pair.id] = pair
            # 清理过期的待配对记录
            self._cleanup_expired_pairs()

        return pair.id

    def capture_rx(self, data: bytes, tx_id: Optional[str] = None) -> None:
        """捕获接收报文。

        :param data: 接收的原始数据
        :type data: bytes
        :param tx_id: 对应的TX事务ID，用于配对
        :type tx_id: Optional[str]
        """
        if not self._enabled:
            return

        record = MessageRecord(direction="RX", data=data)
        self._rx_queue.append(record)

        # 尝试配对
        if tx_id:
            with self._lock:
                if tx_id in self._pending_pairs:
                    pair = self._pending_pairs.pop(tx_id)
                    pair.set_rx(record)
                    self._pairs.append(pair)

    def capture_rx_for_server(self, data: bytes) -> Optional[str]:
        """捕获服务器端接收报文（作为请求）。

        对于服务器端，RX是请求，TX是响应。
        创建配对并返回事务ID，用于后续配对TX响应。

        :param data: 接收的原始数据
        :type data: bytes
        :return: 事务ID，用于后续配对TX
        :rtype: Optional[str]
        """
        if not self._enabled:
            return None

        record = MessageRecord(direction="RX", data=data)
        self._rx_queue.append(record)

        # 创建配对，RX作为请求
        pair = MessagePair()
        pair.set_rx(record)

        with self._lock:
            self._pending_pairs[pair.id] = pair
            self._cleanup_expired_pairs()

        return pair.id

    def capture_tx_for_server(self, data: bytes, rx_id: Optional[str] = None) -> None:
        """捕获服务器端发送报文（作为响应）。

        :param data: 发送的原始数据
        :type data: bytes
        :param rx_id: 对应的RX事务ID，用于配对
        :type rx_id: Optional[str]
        """
        if not self._enabled:
            return

        record = MessageRecord(direction="TX", data=data)
        self._tx_queue.append(record)

        # 尝试配对
        if rx_id:
            with self._lock:
                if rx_id in self._pending_pairs:
                    pair = self._pending_pairs.pop(rx_id)
                    pair.set_tx(record)
                    self._pairs.append(pair)

    def _cleanup_expired_pairs(self) -> None:
        """清理过期的待配对记录。"""
        current_time = time.time()
        expired_ids = []
        for pair_id, pair in self._pending_pairs.items():
            # 检查TX或RX的时间戳
            timestamp = None
            if pair.tx:
                timestamp = pair.tx.timestamp
            elif pair.rx:
                timestamp = pair.rx.timestamp

            if timestamp and (current_time - timestamp) > self._pair_timeout:
                expired_ids.append(pair_id)
                # 将未完成的配对也保存
                self._pairs.append(pair)

        for pair_id in expired_ids:
            del self._pending_pairs[pair_id]

    def get_tx_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取发送报文列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 发送报文列表
        :rtype: List[MessageRecord]
        """
        if count <= 0:
            return self._tx_queue.get_all()
        return self._tx_queue.get_recent(count)

    def get_rx_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取接收报文列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 接收报文列表
        :rtype: List[MessageRecord]
        """
        if count <= 0:
            return self._rx_queue.get_all()
        return self._rx_queue.get_recent(count)

    def get_pairs(self, count: int = 0) -> List[MessagePair]:
        """获取配对列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 配对列表
        :rtype: List[MessagePair]
        """
        if count <= 0:
            return self._pairs.get_all()
        return self._pairs.get_recent(count)

    def get_all_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取所有报文（TX和RX），按时间排序。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 所有报文列表
        :rtype: List[MessageRecord]
        """
        all_messages = self._tx_queue.get_all() + self._rx_queue.get_all()
        all_messages.sort(key=lambda x: x.timestamp)
        if count <= 0:
            return all_messages
        return all_messages[-count:]

    def clear(self) -> None:
        """清空所有捕获的报文。"""
        self._tx_queue.clear()
        self._rx_queue.clear()
        self._pairs.clear()
        with self._lock:
            self._pending_pairs.clear()

    def get_stats(self) -> dict:
        """获取捕获统计信息。

        :return: 统计信息字典
        :rtype: dict
        """
        return {
            "enabled": self._enabled,
            "queue_size": self._queue_size,
            "tx_count": len(self._tx_queue),
            "rx_count": len(self._rx_queue),
            "pair_count": len(self._pairs),
            "pending_count": len(self._pending_pairs),
        }
