from setuptools import setup, find_packages
import os

# 读取README文件作为长描述
def read_readme():
    if os.path.exists("README.md"):
        with open("README.md", "r", encoding="utf-8") as f:
            return f.read()
    return "DLT645协议Python实现库"

setup(
    name="dlt645",  # 改为简单的包名
    version="1.0.0",
    author="Chen Dongyu",
    author_email="1755696012@qq.com",
    description="DLT645协议Python实现库",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://gitee.com/chen-dongyu123/dlt645",
    
    # 重新组织包结构，将src内容作为dlt645包
    packages=["dlt645", "dlt645.common", "dlt645.model", "dlt645.model.data", "dlt645.model.data.define", "dlt645.model.types", "dlt645.protocol", "dlt645.service", "dlt645.service.clientsvc", "dlt645.service.serversvc", "dlt645.transport", "dlt645.transport.client", "dlt645.transport.server"],
    package_dir={"dlt645": "src"},
    
    # 包含配置文件和其他数据文件
    package_data={
        "dlt645": ["config/*.json"],
    },
    include_package_data=True,
    
    # 依赖库
    install_requires=[
        "loguru>=0.5.0",
        "pyserial>=3.4",
    ],
    
    # 可选依赖
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
        ],
    },
    
    # 分类信息
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Communications",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    
    python_requires=">=3.7",
    
    # 项目关键词
    keywords="dlt645 protocol communication energy meter",
    
    # 项目主页
    project_urls={
        "Bug Reports": "https://gitee.com/chen-dongyu123/dlt645/issues",
        "Source": "https://gitee.com/chen-dongyu123/dlt645",
    },
)
