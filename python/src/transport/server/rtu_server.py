from typing import Optional, Any
import serial
import threading
import time

from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class RtuServer:
    def __init__(
            self,
            port: str,
            data_bits: int = 8,
            stop_bits: int = 1,
            baud_rate: int = 9600,
            parity: str = serial.PARITY_NONE,
            timeout: float = 1.0,
            service=None
    ):
        self.port = port
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.baud_rate = baud_rate
        self.parity = parity
        self.timeout = timeout
        self.service = service
        self.conn: Optional[serial.Serial] = None
        self._server_thread = None
        self._running = False
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """启动RTU服务器（非阻塞，在后台线程中运行）"""
        if self._running:
            log.warning("RTU server is already running")
            return True
            
        self._stop_event.clear()
        self._running = True
        
        # 在后台线程中启动服务器
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        
        # 等待服务器启动完成
        time.sleep(0.1)
        log.info(f"RTU server starting in background on {self.port}")
        return True
    
    def _run_server(self):
        """服务器主循环（在后台线程中运行）"""
        try:
            self.conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                stopbits=self.stop_bits,
                parity=self.parity,
                timeout=self.timeout
            )

            log.info(f"RTU server started on port {self.port}")

            # 启动连接处理循环
            self.handle_connection(self.conn)

        except Exception as e:
            log.error(f"Failed to open serial port: {e}")
        finally:
            self._running = False
            if self.conn:
                try:
                    self.conn.close()
                    self.conn = None
                except:
                    pass
            log.info("RTU server stopped")

    def stop(self) -> bool:
        """停止RTU服务器"""
        if not self._running:
            log.warning("RTU server is not running")
            return True
            
        log.info("Shutting down RTU server...")
        
        # 设置停止信号
        self._stop_event.set()
        
        # 关闭串口连接
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
            except Exception as e:
                log.error(f"Error closing serial connection: {e}")
        
        # 等待服务器线程结束
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
            if self._server_thread.is_alive():
                log.warning("Server thread did not stop gracefully")
        
        self._running = False
        log.info("RTU server shutdown complete")
        return True
    
    def is_running(self) -> bool:
        """检查服务器是否正在运行"""
        return self._running

    def handle_connection(self, conn: Any) -> None:
        if not isinstance(conn, serial.Serial):
            log.error(f"Invalid connection type: {type(conn)}")
            return

        try:
            while not self._stop_event.is_set():
                # 读取数据（使用较短的超时以便检查停止信号）
                data = conn.read(256)
                if not data:
                    # 短暂等待以避免CPU占用过高
                    time.sleep(0.01)
                    continue

                log.info(f"Received data: {bytes_to_spaced_hex(data)}")

                # 协议解析
                try:
                    frame = DLT645Protocol.deserialize(data)
                except Exception as e:
                    log.error(f"Error parsing frame: {e}")
                    continue

                # 业务处理
                if self.service is None:
                    log.warning("No service configured to handle request")
                    continue

                try:
                    resp = self.service.handle_request(frame)
                except Exception as e:
                    log.error(f"Error handling request: {e}")
                    continue

                # 响应
                if resp is not None:
                    try:
                        conn.write(resp)
                        log.info(f"Sent response: {bytes_to_spaced_hex(resp)}")
                    except Exception as e:
                        log.error(f"Error writing response: {e}")
                        continue

        except Exception as e:
            if not self._stop_event.is_set():
                log.error(f"Connection handling error: {e}")
        finally:
            try:
                if conn and conn.is_open:
                    conn.close()
            except Exception as e:
                log.error(f"Error closing connection: {e}")
