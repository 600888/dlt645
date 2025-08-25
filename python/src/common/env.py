import os

current_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(os.path.dirname(current_path))
conf_path = os.path.join(root_path, 'config')
log_path = os.path.join(root_path, 'log')
