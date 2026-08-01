"""线程式 DL/T 645 TCP 服务端。"""

import socket
import threading
from typing import Any, Optional

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class TcpServer:
    """为每条 TCP 连接创建一个工作线程的服务端。"""

    MAX_BUFFER_SIZE = 4096

    def __init__(
        self,
        ip: str,
        port: int,
        timeout: float = 5.0,
        service: Any = None,
    ) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.service = service
        self.ln: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._client_threads: set[threading.Thread] = set()
        self._running = False
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._connections: set[socket.socket] = set()
        self._connections_lock = threading.Lock()
        self._message_capture: Optional[MessageCapture] = None

    def start(self) -> bool:
        """启动监听并等待绑定完成；重复调用是幂等的。"""
        if self._running:
            return True
        if self._server_thread is not None and self._server_thread.is_alive():
            return False

        self._stop_event.clear()
        self._started_event.clear()
        self._server_thread = threading.Thread(
            target=self._run_server,
            name=f"dlt645-tcp-{self.ip}:{self.port}",
            daemon=True,
        )
        self._server_thread.start()
        if not self._started_event.wait(timeout=min(max(self.timeout, 1.0), 5.0)):
            log.error("TCP server startup timed out")
            self.stop()
            return False
        return self._running

    def _run_server(self) -> None:
        listener: Optional[socket.socket] = None
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.settimeout(0.5)
            listener.bind((self.ip, self.port))
            listener.listen()
            self.ln = listener
            if self.port == 0:
                self.port = listener.getsockname()[1]
            self._running = True
            self._started_event.set()
            log.info(f"TCP server started on {self.ip}:{self.port}")

            while not self._stop_event.is_set():
                try:
                    conn, addr = listener.accept()
                except socket.timeout:
                    continue
                except OSError as exc:
                    if self._stop_event.is_set():
                        break
                    log.error(f"Failed to accept connection: {exc}")
                    continue

                conn.settimeout(self.timeout)
                with self._connections_lock:
                    self._connections.add(conn)
                worker = threading.Thread(
                    target=self.handle_connection,
                    args=(conn,),
                    name=f"dlt645-client-{addr}",
                    daemon=True,
                )
                with self._connections_lock:
                    self._client_threads.add(worker)
                worker.start()
        except BaseException as exc:
            log.error(f"TCP server failed: {exc}")
        finally:
            self._running = False
            self._started_event.set()
            self.ln = None
            if listener is not None:
                try:
                    listener.close()
                except OSError:
                    pass
            log.info("TCP server stopped")

    def stop(self) -> bool:
        """关闭监听、活动连接和工作线程；重复调用是幂等的。"""
        self._stop_event.set()
        listener, self.ln = self.ln, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass

        with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()
        for conn in connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass

        current = threading.current_thread()
        if self._server_thread is not None and self._server_thread is not current:
            self._server_thread.join(timeout=5.0)
        with self._connections_lock:
            workers = list(self._client_threads)
        for worker in workers:
            if worker is not current:
                worker.join(timeout=1.0)
        self._running = False
        return self._server_thread is None or not self._server_thread.is_alive()

    def is_running(self) -> bool:
        return self._running

    def _dispatch(self, frame: Any) -> Optional[bytes]:
        if self.service is None:
            raise RuntimeError("TCP server is not bound to a service")
        result = self.service.handle_request(frame)
        return None if result is None else bytes(result)

    def handle_connection(self, conn: socket.socket) -> None:
        data_buffer = bytearray()
        try:
            while not self._stop_event.is_set():
                try:
                    chunk = conn.recv(1024)
                except socket.timeout:
                    if data_buffer:
                        log.warning("TCP incomplete frame timed out; buffer cleared")
                        data_buffer.clear()
                    continue
                if not chunk:
                    break

                data_buffer.extend(chunk)
                log.info(f"RX: {bytes_to_spaced_hex(chunk)}")
                if len(data_buffer) > self.MAX_BUFFER_SIZE:
                    log.warning("TCP receive buffer overflow; buffer cleared")
                    data_buffer.clear()
                    continue

                while data_buffer:
                    original = bytes(data_buffer)
                    remaining, frame = DLT645Protocol.deserialize_with_remaining(
                        original
                    )
                    if frame is None:
                        if remaining != original:
                            data_buffer = bytearray(remaining)
                            continue
                        break

                    consumed = len(original) - len(remaining)
                    request = original[:consumed]
                    data_buffer = bytearray(remaining)
                    pair_id: Optional[str] = None
                    if self._message_capture:
                        pair_id = self._message_capture.capture_rx_for_server(request)

                    response = self._dispatch(frame)
                    if response:
                        conn.sendall(response)
                        log.info(f"TX: {bytes_to_spaced_hex(response)}")
                        if self._message_capture:
                            self._message_capture.capture_tx_for_server(
                                response, pair_id
                            )
        except (ConnectionError, OSError) as exc:
            if not self._stop_event.is_set():
                log.error(f"TCP connection failed: {exc}")
        except Exception as exc:
            log.error(f"TCP request handling failed: {exc}")
        finally:
            with self._connections_lock:
                self._connections.discard(conn)
                self._client_threads.discard(threading.current_thread())
            try:
                conn.close()
            except OSError:
                pass

    def __enter__(self) -> "TcpServer":
        if not self.start():
            raise OSError(f"无法监听 {self.ip}:{self.port}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
