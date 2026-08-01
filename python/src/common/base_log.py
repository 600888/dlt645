import inspect
import json
from loguru import logger
import os
import sys
import threading
from typing import Optional, Union

LOG_COLORS = {
    "DEBUG": "\033[1;36m",  # CYAN
    "INFO": "\033[1;32m",  # GREEN
    "WARNING": "\033[1;33m",  # YELLOW
    "ERROR": "\033[1;31m",  # RED
    "CRITICAL": "\033[1;31m",  # RED
    "EXCEPTION": "\033[1;31m",  # RED
}
COLOR_RESET = "\033[1;0m"

# ==================== 全局日志配置 ====================
# 默认关闭日志输出：仅当 configure_logging(enabled=True) 被调用后，
# 才会挂载 handler 输出日志。
# None 表示"未配置，回退到各 Log 实例自身的参数/默认值"。
_settings = {
    "enabled": False,  # 默认关闭
    "cmdlevel": None,  # 控制台级别
    "filelevel": None,  # 文件级别
    "filename": None,  # 统一日志文件；None=各模块默认文件
    "backup_count": None,
    "limit": None,
    "when": None,
    "colorful": None,
    "compression": None,
    "is_backtrace": None,
}

# 哨兵：区分"未传参"（保持当前配置）与"显式传 None"（恢复默认）
_UNSET = object()

_lock = threading.Lock()
_loggers: list = []  # 已创建的所有 Log 实例

# 全局 handler 管理（由 configure_logging 统一维护，避免重复输出）
_stderr_handler_id: Optional[int] = None
_file_handler_ids: dict = {}  # filename -> handler id


def _is_lib_record(record) -> bool:
    """库日志消息标记：所有 Log 实例发出时都 bind 了字符串 task。"""
    return isinstance(record["extra"].get("task"), str)


def _first_log() -> Optional["Log"]:
    return _loggers[0] if _loggers else None


def _instance_for_file(filename: str) -> Optional["Log"]:
    """返回使用该有效文件名的第一个实例（用于读取实例级参数）。"""
    for log in _loggers:
        if log._effective_filename() == filename:
            return log
    return None


def _effective_cmdlevel() -> str:
    if _settings["cmdlevel"]:
        return _settings["cmdlevel"]
    lg = _first_log()
    return lg.cmdlevel if lg else "DEBUG"


def _effective_filelevel(filename: str) -> str:
    if _settings["filelevel"]:
        return _settings["filelevel"]
    lg = _instance_for_file(filename)
    return lg.filelevel if lg else "DEBUG"


def _effective_backup_count(filename: str) -> int:
    if _settings["backup_count"] is not None:
        return _settings["backup_count"]
    lg = _instance_for_file(filename)
    return lg.backup_count if lg else 7


def _effective_limit(filename: str):
    if _settings["limit"] is not None:
        return _settings["limit"]
    lg = _instance_for_file(filename)
    return lg.limit if lg else "20 MB"


def _effective_when(filename: str):
    if _settings["when"] is not None:
        return _settings["when"]
    lg = _instance_for_file(filename)
    return lg.when if lg else None


def _effective_colorful() -> bool:
    if _settings["colorful"] is not None:
        return _settings["colorful"]
    lg = _first_log()
    return lg.colorful if lg else True


def _effective_compression(filename: str):
    if _settings["compression"] is not None:
        return _settings["compression"]
    lg = _instance_for_file(filename)
    return lg.compression if lg else None


def _effective_is_backtrace() -> bool:
    if _settings["is_backtrace"] is not None:
        return _settings["is_backtrace"]
    lg = _first_log()
    return lg.is_backtrace if lg else True


def _formatter(record) -> str:
    """全局日志格式（模块级，避免依赖实例状态）。"""
    # 处理消息内容
    message = record["message"]
    if isinstance(message, (dict, list)):
        try:
            message = json.dumps(message, ensure_ascii=False)
        except TypeError:
            message = str(message)
    message = str(message).replace("{", "{{").replace("}", "}}")

    # 处理调用栈和颜色
    if _effective_is_backtrace():
        frame = inspect.currentframe()
        while frame:
            if (
                "loguru" not in frame.f_code.co_filename
                and "base_log.py" not in frame.f_code.co_filename
            ):
                break
            frame = frame.f_back
        file_info = (
            f"[{os.path.basename(frame.f_code.co_filename)}:{frame.f_code.co_name}:{frame.f_lineno}]"
            if frame
            else f"[{record['file']}:{record['function']}:{record['line']}]"
        )
    else:
        file_info = f"[{record['file']}:{record['line']}]"

    # 转义 '<' '>'：co_name 可能是 <module> 等，loguru colorize 会把 <> 当作颜色标签
    file_info = file_info.replace("<", "\\<").replace(">", "\\>")

    level_color = LOG_COLORS.get(record["level"].name, "")
    return (
        f"{level_color}[{record['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] "
        + file_info
        + f"[{record['level']}] {message}{COLOR_RESET}\n"
    )


def _get_rotation_config(when: Optional[str], limit: Union[int, str]):
    if when:  # 时间轮转
        return when  # "D"（天）、"H"（小时）、"midnight"等
    else:  # 大小轮转
        if isinstance(limit, int):
            return f"{limit / 1024 / 1024} MB"
        return limit  # 直接支持"10 MB"、"1 GB"等字符串格式


def _ensure_log_dir(filename: str) -> None:
    log_dir = os.path.abspath(os.path.dirname(filename))
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)


def _install() -> None:
    """挂载全局 stderr handler 和文件 handler（按文件分组或统一文件）。"""
    global _stderr_handler_id
    if _stderr_handler_id is None:
        _stderr_handler_id = logger.add(
            sys.stderr,
            level=_effective_cmdlevel(),
            format=_formatter,
            colorize=_effective_colorful(),
            backtrace=True,
            enqueue=True,
            filter=_is_lib_record,  # 只输出库日志
        )

    unified = _settings["filename"]
    if unified:
        # 统一文件模式：所有库日志写入同一文件
        if unified not in _file_handler_ids:
            _ensure_log_dir(unified)
            _file_handler_ids[unified] = logger.add(
                unified,
                level=_effective_filelevel(unified),
                format=_formatter,
                backtrace=True,
                rotation=_get_rotation_config(_effective_when(unified), _effective_limit(unified)),
                retention=f"{_effective_backup_count(unified)} days",
                compression=_effective_compression(unified),
                enqueue=True,
                filter=_is_lib_record,
            )
    else:
        # 分文件模式：按各实例默认文件分组
        for log in _loggers:
            fn = log._effective_filename()
            if fn in _file_handler_ids:
                continue
            _ensure_log_dir(fn)
            _file_handler_ids[fn] = logger.add(
                fn,
                level=_effective_filelevel(fn),
                format=_formatter,
                backtrace=True,
                rotation=_get_rotation_config(_effective_when(fn), _effective_limit(fn)),
                retention=f"{_effective_backup_count(fn)} days",
                compression=_effective_compression(fn),
                enqueue=True,
                filter=lambda record, _fn=fn: record["extra"].get("task") == _fn,
            )


def _uninstall() -> None:
    """移除全部日志 handler（回到默认关闭状态）。"""
    global _stderr_handler_id
    handler_ids = list(_file_handler_ids.values())
    if _stderr_handler_id is not None:
        handler_ids.append(_stderr_handler_id)
    for handler_id in handler_ids:
        try:
            logger.remove(handler_id)
        except ValueError:
            pass
    _file_handler_ids.clear()
    _stderr_handler_id = None


class Log:
    """DLT645 库日志封装。

    默认不输出任何日志（不挂载 handler）；通过模块级函数
    :func:`configure_logging` 启用并配置日志。

    注意：为保证默认静默，本类在首次创建时会移除 loguru 的默认
    stderr handler（ID 0）。若宿主应用依赖 loguru 默认 handler，
    请在导入本库后自行添加所需的 handler。
    """

    # 静态标记：确保只移除一次默认 handler
    _default_handler_removed = False

    def __init__(
        self,
        filename: Optional[str] = None,
        cmdlevel: str = "DEBUG",
        filelevel: str = "INFO",
        backup_count: int = 7,  # 默认保留7天/7个文件
        limit: Union[int, str] = "20 MB",  # 支持字符串格式
        when: Optional[str] = None,
        colorful: bool = True,
        compression: Optional[str] = None,
        is_backtrace: bool = True,
    ):
        # 只移除 loguru 默认的 stderr handler (ID 0)，避免删除其他模块已添加的 handlers
        if not Log._default_handler_removed:
            try:
                logger.remove(0)  # 只移除默认 handler
            except ValueError:
                pass  # 默认 handler 可能已被移除
            Log._default_handler_removed = True

        # 规范化文件名（task 标记与 self.filename 保持一致）
        if filename is None:
            filename = getattr(sys.modules["__main__"], "__file__", "log.py")
            filename = os.path.basename(filename.replace(".py", ".log"))
        self.filename = filename
        self.logger = logger.bind(task=filename)

        # 实例自身的日志参数（全局未配置时作为回退值）
        self.cmdlevel = cmdlevel
        self.filelevel = filelevel
        self.backup_count = backup_count
        self.limit = limit
        self.when = when
        self.colorful = colorful
        self.compression = compression
        self.is_backtrace = is_backtrace

        # 注册实例
        with _lock:
            _loggers.append(self)
            # 默认关闭：仅当全局已启用时才确保 handler 挂载
            if _settings["enabled"]:
                _install()

    def _effective_filename(self) -> str:
        """实际使用的日志文件名（全局统一文件名优先，不修改实例默认值）。"""
        if _settings["filename"]:
            return _settings["filename"]
        return self.filename

    def set_config(
        self,
        filename: Optional[str] = None,
        cmdlevel: str = "DEBUG",
        filelevel: str = "INFO",
        backup_count: int = 7,
        limit: Union[int, str] = "20 MB",
        when: Optional[str] = None,
        colorful: bool = True,
        compression: Optional[str] = None,
    ):
        """动态修改本实例的日志配置（作为全局未配置时的默认值）。

        仅当全局日志已启用时立即生效；否则下次启用时生效。
        """
        if filename is not None:
            self.filename = filename
            self.logger = logger.bind(task=filename)
        self.cmdlevel = cmdlevel
        self.filelevel = filelevel
        self.backup_count = backup_count
        self.limit = limit
        self.when = when
        self.colorful = colorful
        self.compression = compression

        # 重建全局 handler（filename 变化可能改变文件分组）
        with _lock:
            if _settings["enabled"]:
                _uninstall()
                _install()

    @staticmethod
    def set_logger(**kwargs) -> bool:
        """For backward compatibility."""
        return True

    def enable_log(self) -> None:
        """启用本库日志输出（全局开关）。

        兼容接口，等价于 :func:`configure_logging`(enabled=True)。
        """
        configure_logging(enabled=True)

    def disable_log(self) -> None:
        """关闭本库日志输出（全局开关）。

        兼容接口，等价于 :func:`configure_logging`(enabled=False)。
        """
        configure_logging(enabled=False)

    def set_log_level(
        self, level: str, is_console: bool = True, is_file: bool = True
    ) -> bool:
        """设置日志级别（全局生效）。

        :param level: 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
        :type level: str
        :param is_console: 是否应用到控制台输出。
        :type is_console: bool
        :param is_file: 是否应用到文件输出。
        :type is_file: bool
        :return: 级别有效返回 True，无效返回 False。
        :rtype: bool
        """
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        level = str(level).upper()
        if level not in valid_levels:
            return False

        with _lock:
            if is_console:
                self.cmdlevel = level
                _settings["cmdlevel"] = level
            if is_file:
                self.filelevel = level
                _settings["filelevel"] = level
            if _settings["enabled"]:
                _uninstall()
                _install()
        return True

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)

    def exception(self, *args, **kwargs):
        self.logger.exception(*args, **kwargs)


# ==================== 开放配置接口 ====================


def configure_logging(
    enabled: bool = True,
    cmdlevel: Optional[str] = None,
    filelevel: Optional[str] = None,
    filename: Union[str, None, object] = _UNSET,
    backup_count: Optional[int] = None,
    limit: Union[int, str, None] = None,
    when: Optional[str] = None,
    colorful: Optional[bool] = None,
    compression: Optional[str] = None,
    is_backtrace: Optional[bool] = None,
) -> None:
    """配置 dlt645 库的日志输出。

    库默认**不输出任何日志**；调用本函数启用日志或调整日志配置。

    :param enabled: True 启用日志输出，False 关闭（移除所有日志 handler）。
    :type enabled: bool
    :param cmdlevel: 控制台日志级别（如 "DEBUG"/"INFO"/"WARNING"/"ERROR"）。
        None 表示回退到各模块默认级别。
    :type cmdlevel: Optional[str]
    :param filelevel: 文件日志级别。None 表示回退到各模块默认级别。
    :type filelevel: Optional[str]
    :param filename: 统一日志文件路径；指定后所有模块日志输出到该文件。
        传 None 恢复"各模块各自文件"；不传（默认）保持当前配置。
    :type filename: Union[str, None, object]
    :param backup_count: 日志文件保留数量（天）。
    :type backup_count: Optional[int]
    :param limit: 单文件大小限制（如 "10 MB"）。
    :type limit: Union[int, str, None]
    :param when: 按时间轮转（如 "midnight"、"D"、"H"）。
    :type when: Optional[str]
    :param colorful: 控制台输出是否带颜色。
    :type colorful: Optional[bool]
    :param compression: 轮转文件压缩格式（如 "zip"）。
    :type compression: Optional[str]
    :param is_backtrace: 是否显示调用位置（文件:函数:行号）。
    :type is_backtrace: Optional[bool]

    示例::

        from dlt645 import configure_logging

        # 启用日志，控制台 INFO、文件 DEBUG
        configure_logging(cmdlevel="INFO", filelevel="DEBUG")

        # 所有日志统一写入指定文件
        configure_logging(filename="logs/meter.log")

        # 恢复各模块各自文件
        configure_logging(filename=None)

        # 关闭日志
        configure_logging(enabled=False)
    """
    with _lock:
        if enabled is not None:
            _settings["enabled"] = enabled
        if cmdlevel is not None:
            _settings["cmdlevel"] = cmdlevel
        if filelevel is not None:
            _settings["filelevel"] = filelevel
        if filename is not _UNSET:  # 显式传 filename 或 None 都生效
            _settings["filename"] = filename
        if backup_count is not None:
            _settings["backup_count"] = backup_count
        if limit is not None:
            _settings["limit"] = limit
        if when is not None:
            _settings["when"] = when
        if colorful is not None:
            _settings["colorful"] = colorful
        if compression is not None:
            _settings["compression"] = compression
        if is_backtrace is not None:
            _settings["is_backtrace"] = is_backtrace

        # 重建全部 handler 以应用新配置
        _uninstall()
        if _settings["enabled"]:
            _install()


def enable_logging(**kwargs) -> None:
    """启用 dlt645 库日志输出（可传 :func:`configure_logging` 的参数）。"""
    configure_logging(enabled=True, **kwargs)


def disable_logging() -> None:
    """关闭 dlt645 库日志输出。"""
    configure_logging(enabled=False)
