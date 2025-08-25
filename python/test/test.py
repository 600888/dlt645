import json

from src.common import root_path


def fix_dataformat_key(data_list):
    """
    将列表中的Dataformat键改为DataFormat
    """

    fixed_data = []
    for item in data_list:
        # 创建新字典，修改键名
        new_item = item.copy()
        if "Dataformat" in new_item:
            new_item["DataFormat"] = new_item.pop("Dataformat")
        fixed_data.append(new_item)
    return fixed_data


# 执行修改
# 读取数据
with open(root_path + '/config/variable_types.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fixed_data = fix_dataformat_key(data)

# 输出结果
print("修改后的数据:")
print(json.dumps(fixed_data, ensure_ascii=False, indent=4))

# 如果需要保存到文件
with open(root_path + '/config/variable_types.json', 'w', encoding='utf-8') as f:
    json.dump(fixed_data, f, ensure_ascii=False, indent=4)
