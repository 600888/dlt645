import os

# 在包安装模式下，使用__file__获取目前模块的路径
current_path = os.path.dirname(os.path.abspath(__file__))
# dlt645/common/env.py -> dlt645/
package_root = os.path.dirname(current_path)
conf_path = os.path.join(package_root, 'config')
log_path = os.path.join(package_root, 'log')

# 如果配置目录不存在，尝试使用相对路径（开发模式）
if not os.path.exists(conf_path):
    # 开发模式下的路径结构
    root_path = os.path.dirname(os.path.dirname(current_path))
    log_path = os.path.join(root_path, 'log')
    src_path = os.path.join(root_path, 'src')
    conf_path = os.path.join(src_path, 'config')
