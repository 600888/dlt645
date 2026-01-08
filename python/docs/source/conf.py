# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('../..'))

project = 'dlt645'
copyright = '2026, 陈东宇'
author = '陈东宇'
release = 'v1.4.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ['_templates']
exclude_patterns = []

language = 'zh'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# 扩展模块
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    'sphinx_copybutton',
]

# 模板路径
templates_path = ['_templates']

# 排除的文件
exclude_patterns = []

# 主文档名称
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# 主题名称
html_theme = 'sphinx_rtd_theme'

# 主题配置选项
html_theme_options = {
    # 导航菜单默认展开，不折叠
    'collapse_navigation': False,
    # 显示完整的目录树结构
    'navigation_depth': -1,
}

# 静态资源路径
html_static_path = ['_static']

# -- Options for autodoc ----------------------------------------------------

# 自动文档生成选项
autodoc_member_order = 'bysource'
autoclass_content = 'both'

# -- Options for intersphinx -------------------------------------------------

# 交叉引用配置
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}