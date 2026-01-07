import inspect
from loguru import logger
import os
import sys
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

logger.remove(0)


class Log:
    def __init__(
        self,
        filename: Optional[str] = None,
        cmdlevel: str = "DEBUG",
        filelevel: str = "INFO",
        backup_count: int = 7,  # 默认保留7天/7个文件
        limit: Union[int, str] = "20 MB",  # 支持字符串格式
        when: Optional[str] = None,
        colorful: bool = True,
        compression: Optional[str] = None,  # 新增压缩功能
        is_backtrace: bool = True,
    ):
        self.is_backtrace = is_backtrace
        self.logger = logger.bind(task=filename)
        self.filename = filename
        # 设置日志文件路径
        if filename is None:
            filename = getattr(sys.modules["__main__"], "__file__", "log.py")
            filename = os.path.basename(filename.replace(".py", ".log"))
            self.filename = filename

        # 确保日志目录存在
        log_dir = os.path.abspath(os.path.dirname(filename))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 保存初始配置
        self.cmdlevel = cmdlevel
        self.filelevel = filelevel
        self.colorful = colorful
        self.compression = compression
        self.backup_count = backup_count
        self.when = when
        self.limit = limit
        self.is_enabled = True
        
        # 存储 sink IDs
        self.cmd_sink_id = None
        self.file_sink_id = None
        
        # 初始化日志
        self._init_loggers()
    
    def _init_loggers(self):
        """初始化日志输出器"""
        # 控制台输出配置
        self.cmd_sink_id = self.logger.add(
            sys.stderr,
            level=self.cmdlevel,
            format=self._formatter,
            colorize=self.colorful,
            backtrace=True,
            enqueue=False,  # 控制台输出同步写入
            filter=self._get_filter_func(),
        )

        # 文件输出配置
        rotation_config = self._get_rotation_config(self.when, self.limit)
        self.file_sink_id = self.logger.add(
            self.filename,
            level=self.filelevel,
            format=self._formatter,
            backtrace=True,
            rotation=rotation_config,
            retention=f"{self.backup_count} days",
            compression=self.compression,
            enqueue=True,
            filter=self._get_filter_func(),
        )
    
    def _get_filter_func(self):
        """获取日志过滤器函数"""
        def filter_func(record):
            # 如果日志被禁用，则不输出任何日志
            if not self.is_enabled:
                return False
            # 正常的任务过滤
            return record["extra"]["task"] == self.filename
        return filter_func

    def _formatter(self, record):
        if self.is_backtrace:
            # 获取调用栈，跳过 Loguru 和工具类的帧
            frame = inspect.currentframe()
            while frame:
                # 排除 Loguru 内部调用和工具类自身的帧
                if (
                    "loguru" not in frame.f_code.co_filename
                    and "log.py" not in frame.f_code.co_filename
                ):
                    break
                frame = frame.f_back

            # 动态获取调用函数名、文件名和行号
            func_name = frame.f_code.co_name if frame else record["function"]
            file_name = (
                os.path.basename(frame.f_code.co_filename) if frame else record["file"]
            )
            line_no = frame.f_lineno if frame else record["line"]
            file_info = f"[{file_name}:{func_name}:{line_no}] "
        else:
            file_info = f"[{record['file']}:{record['line']}]"
        level_color = LOG_COLORS.get(record["level"].name, "")
        return (
            f"{level_color}[{record['time'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] "
            + file_info
            + f"[{record['level']}] {record['message']}{COLOR_RESET}\n"
        )

    def _get_rotation_config(self, when: Optional[str], limit: Union[int, str]):
        if when:  # 时间轮转
            return when  # "D"（天）、"H"（小时）、"midnight"等
        else:  # 大小轮转
            if isinstance(limit, int):
                return f"{limit / 1024 / 1024} MB"
            return limit  # 直接支持"10 MB"、"1 GB"等字符串格式

    @staticmethod
    def set_logger(**kwargs) -> bool:
        """For backward compatibility."""
        return True
    
    def set_log_enable(self, enable: bool = True):
        """开启日志功能"""
        self.is_enabled = enable
        return True
    
    def set_log_level(self, level: str, is_console: bool = True, is_file: bool = True):
        """设置日志等级

        Args:
            level: 日志等级 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            is_console: 是否设置控制台日志等级
            is_file: 是否设置文件日志等级
            
        Returns:
            bool: 设置是否成功
        """
        # 验证日志等级
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() not in valid_levels:
            self.error(f"Invalid log level: {level}. Valid levels are: {', '.join(valid_levels)}")
            return False
        
        # 更新存储的日志等级
        if is_console:
            self.cmdlevel = level.upper()
            # 移除并重新添加控制台输出器以更新等级
            if self.cmd_sink_id is not None:
                self.logger.remove(self.cmd_sink_id)
                self.cmd_sink_id = self.logger.add(
                    sys.stderr,
                    level=self.cmdlevel,
                    format=self._formatter,
                    colorize=self.colorful,
                    backtrace=True,
                    enqueue=False,
                    filter=self._get_filter_func(),
                )
        
        if is_file:
            self.filelevel = level.upper()
            # 移除并重新添加文件输出器以更新等级
            if self.file_sink_id is not None:
                self.logger.remove(self.file_sink_id)
                rotation_config = self._get_rotation_config(self.when, self.limit)
                self.file_sink_id = self.logger.add(
                    self.filename,
                    level=self.filelevel,
                    format=self._formatter,
                    backtrace=True,
                    rotation=rotation_config,
                    retention=f"{self.backup_count} days",
                    compression=self.compression,
                    enqueue=True,
                    filter=self._get_filter_func(),
                )
        
        return True
    
    def set_config(self, **kwargs):
        """设置日志配置参数
        
        Args:
            \**kwargs: 支持更新的参数，包括：
                filename: 日志文件名
                cmdlevel: 控制台日志等级
                filelevel: 文件日志等级
                backup_count: 保留的日志文件数量
                limit: 日志文件大小限制
                when: 日志轮转时间配置
                colorful: 是否启用彩色输出
                compression: 压缩格式
                is_backtrace: 是否启用回溯
            
        Returns:
            bool: 更新是否成功
        """
        # 验证并更新参数
        if 'cmdlevel' in kwargs or 'filelevel' in kwargs:
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            for level_key in ['cmdlevel', 'filelevel']:
                if level_key in kwargs:
                    if kwargs[level_key].upper() not in valid_levels:
                        self.error(f"Invalid {level_key}: {kwargs[level_key]}. Valid levels are: {', '.join(valid_levels)}")
                        return False
                    setattr(self, level_key, kwargs[level_key].upper())
        
        # 更新其他参数
        for param in ['backup_count', 'limit', 'when', 'colorful', 'compression', 'is_backtrace']:
            if param in kwargs:
                setattr(self, param, kwargs[param])
        
        # 特殊处理filename参数，需要重新绑定task
        if 'filename' in kwargs:
            self.filename = kwargs['filename']
            # 确保日志目录存在
            log_dir = os.path.abspath(os.path.dirname(self.filename))
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            # 重新绑定logger的task属性
            self.logger = logger.bind(task=self.filename)
        
        # 重新初始化日志输出器
        if self.cmd_sink_id is not None:
            self.logger.remove(self.cmd_sink_id)
        if self.file_sink_id is not None:
            self.logger.remove(self.file_sink_id)
        
        self._init_loggers()
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
