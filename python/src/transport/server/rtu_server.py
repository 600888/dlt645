from typing import Optional, Any
import serial

from src.common.transform import bytes_to_spaced_hex
from src.protocol.protocol import DLT645Protocol
from src.transport.server.log import log


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

    def start(self) -> bool:
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

            # 启动连接处理线程
            self.handle_connection(self.conn)
            return True

        except Exception as e:
            log.error(f"Failed to open serial port: {e}")
            return False

    def stop(self) -> bool:
        if self.conn is not None:
            log.info("Shutting down RTU server...")
            self.conn.close()
            self.conn = None
            return True
        return False

    def handle_connection(self, conn: Any) -> None:
        if not isinstance(conn, serial.Serial):
            log.error(f"Invalid connection type: {type(conn)}")
            return

        try:
            while True:
                # 读取数据
                data = conn.read(256)
                if not data:
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
            log.error(f"Connection handling error: {e}")
        finally:
            try:
                conn.close()
            except Exception as e:
                log.error(f"Error closing connection: {e}")
