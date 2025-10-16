import os

from ...common.base_log import Log
from ...common.env import log_path

log = Log(filename=os.path.join(log_path, "clientsvc.log"), when='10 MB', cmdlevel='DEBUG',
          filelevel='DEBUG', limit="10 MB", backup_count=1, colorful=True)