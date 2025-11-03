#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV转JSON工具
功能：读取CSV文件，生成符合DLT645格式的JSON列表
"""

import csv
import json
import os
import argparse


def csv_to_json(csv_file_path, json_file_path=None):
    """
    读取CSV文件并转换为JSON格式
    
    Args:
        csv_file_path: CSV文件路径
        json_file_path: 输出的JSON文件路径，如果不指定则在CSV文件同目录生成
    
    Returns:
        list: 转换后的JSON数据列表
    """
    print(f"调试：输入CSV文件路径 - {csv_file_path}")
    print(f"调试：输出JSON文件路径 - {json_file_path}")
    
    # 检查CSV文件是否存在
    if not os.path.exists(csv_file_path):
        print(f"错误：CSV文件不存在 - {csv_file_path}")
        return []
    
    # 如果未指定JSON输出路径，则在CSV文件同目录生成
    if json_file_path is None:
        csv_dir = os.path.dirname(csv_file_path)
        csv_filename = os.path.basename(csv_file_path)
        json_filename = os.path.splitext(csv_filename)[0] + '.json'
        json_file_path = os.path.join(csv_dir, json_filename)
    elif os.path.isdir(json_file_path):
        # 如果输出路径是目录，则在该目录下生成与CSV同名的JSON文件
        csv_filename = os.path.basename(csv_file_path)
        json_filename = os.path.splitext(csv_filename)[0] + '.json'
        json_file_path = os.path.join(json_file_path, json_filename)
    
    print(f"调试：最终输出JSON文件路径 - {json_file_path}")
    
    # 定义字段映射，CSV列名到JSON字段名的映射
    # 根据实际CSV文件的列名进行配置
    field_mapping = {
        '数据标识': 'Di',        # 数据标识
        '数据项描述': 'Name',    # 中文名称
        '数据格式': 'DataFormat'  # 数据格式
    }
    print(f"调试：字段映射配置 - {field_mapping}")
    
    json_data = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            
            # 获取CSV文件的所有列名
            csv_columns = csv_reader.fieldnames
            if not csv_columns:
                print("错误：CSV文件没有列头")
                return []
            
            print(f"调试：CSV文件列名 - {csv_columns}")
            
            # 检查必需的列是否存在
            missing_columns = []
            for required_col in field_mapping.keys():
                if required_col not in csv_columns:
                    missing_columns.append(required_col)
            
            if missing_columns:
                print(f"警告：CSV文件缺少以下列 - {', '.join(missing_columns)}")
                print("将尝试使用现有列名进行映射")
            
            # 读取每一行数据
            print("调试：开始读取CSV数据行")
            for row_idx, row in enumerate(csv_reader, 1):
                print(f"调试：处理第{row_idx}行 - {row}")
                item = {}
                
                # 特殊处理Di字段，确保正确提取
                if '数据标识' in row:
                    di_raw = row['数据标识'].strip()
                    print(f"调试：原始Di值 - '{di_raw}'")
                    # 移除0x前缀并保持大写
                    if di_raw.startswith('0x'):
                        di_processed = di_raw[2:].upper()
                        print(f"调试：处理后Di值 - '{di_processed}'")
                    else:
                        di_processed = di_raw.upper()
                    item['Di'] = di_processed
                else:
                    print(f"调试：第{row_idx}行没有'数据标识'列")
                    item['Di'] = ''
                
                # 处理其他字段
                for csv_col, json_field in field_mapping.items():
                    # 跳过已经处理过的Di字段
                    if json_field == 'Di':
                        continue
                    
                    if csv_col in row:
                        value = row[csv_col].strip()
                        item[json_field] = value
                        print(f"调试：映射 {csv_col} -> {json_field} = '{value}'")
                    else:
                        print(f"调试：第{row_idx}行没有'{csv_col}'列")
                        item[json_field] = ''
                
                # 确保所有必需的字段都存在
                if 'Name' not in item:
                    item['Name'] = ''
                if 'Unit' not in item:
                    item['Unit'] = ''  # 设置默认单位为空字符串
                if 'DataFormat' not in item:
                    item['DataFormat'] = ''
                
                # 添加数据项（宽松模式，即使Di为空也添加）
                json_data.append(item)
                print(f"调试：已添加数据项 - {item}")
        
        # 写入JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(json_data, json_file, ensure_ascii=False, indent=4)
        
        print(f"成功：JSON文件已生成 - {json_file_path}")
        print(f"总共转换了 {len(json_data)} 条数据")
        
        return json_data
        
    except csv.Error as e:
        print(f"CSV解析错误：{e}")
    except json.JSONDecodeError as e:
        print(f"JSON编码错误：{e}")
    except Exception as e:
        print(f"发生错误：{e}")
    
    return []


def main():
    """
    主函数，处理命令行参数
    """
    parser = argparse.ArgumentParser(description='CSV转JSON工具 - 生成符合DLT645格式的JSON列表')
    parser.add_argument('csv_file', help='CSV文件路径')
    parser.add_argument('-o', '--output', help='输出JSON文件路径（可选，可为目录或文件）')
    parser.add_argument('-p', '--preview', action='store_true', help='预览生成的JSON数据（不保存文件）')
    
    args = parser.parse_args()
    print(f"调试：命令行参数 - csv_file={args.csv_file}, output={args.output}, preview={args.preview}")
    
    # 读取CSV文件并转换为JSON
    json_data = csv_to_json(args.csv_file, None if args.preview else args.output)
    
    # 如果需要预览
    if args.preview and json_data:
        print("\n预览JSON数据（前5条）：")
        preview_data = json_data[:5]
        print(json.dumps(preview_data, ensure_ascii=False, indent=4))
        if len(json_data) > 5:
            print(f"... 还有 {len(json_data) - 5} 条数据未显示")
    
    print(f"调试：转换完成，总共处理了 {len(json_data)} 条数据")


if __name__ == '__main__':
    main()