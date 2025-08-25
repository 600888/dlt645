import os

from src.common.base_log import Log
from src.common.env import log_path

log = Log(filename=os.path.join(log_path, "data.log"), when='10 MB', cmdlevel='DEBUG',
          filelevel='DEBUG', limit="10 MB", backup_count=1, colorful=True)