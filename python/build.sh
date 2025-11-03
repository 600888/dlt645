#!/bin/bash
# DLT645协议包构建脚本

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${2}${1}${NC}"
}

print_success() {
    print_message "$1" "$GREEN"
}

print_warning() {
    print_message "$1" "$YELLOW"
}

print_error() {
    print_message "$1" "$RED"
}

print_info() {
    print_message "$1" "$BLUE"
}

# 检查是否在正确的目录
check_directory() {
    if [ ! -f "setup.py" ] || [ ! -f "pyproject.toml" ]; then
        print_error "错误：请在dlt645包根目录中运行此脚本"
        exit 1
    fi
}

# 清理构建文件
clean_build() {
    print_info "清理构建文件..."
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf __pycache__/
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    print_success "✓ 构建文件清理完成"
}

# 运行基本测试
run_tests() {
    print_info "运行基本测试..."
    if python test/test_basic.py; then
        print_success "✓ 基本测试通过"
    else
        print_error "✗ 基本测试失败"
        exit 1
    fi
}

# 检查依赖
check_dependencies() {
    print_info "检查构建依赖..."
    
    # 检查必要的包
    python -c "import setuptools" 2>/dev/null || {
        print_error "setuptools未安装，正在安装..."
        pip install setuptools
    }
    
    python -c "import wheel" 2>/dev/null || {
        print_error "wheel未安装，正在安装..."
        pip install wheel
    }
    
    python -c "import build" 2>/dev/null || {
        print_warning "build未安装，正在安装..."
        pip install build
    }
    
    print_success "✓ 构建依赖检查完成"
}

# 构建包
build_package() {
    print_info "构建Python包..."
    
    # 使用现代构建工具
    if command -v python -m build &> /dev/null; then
        python -m build
    else
        # 回退到传统方法
        python setup.py sdist bdist_wheel
    fi
    
    print_success "✓ 包构建完成"
}

# 检查构建结果
check_build() {
    print_info "检查构建结果..."
    
    if [ -d "dist" ]; then
        print_info "构建的文件："
        ls -la dist/
        
        # 检查wheel文件
        wheel_count=$(ls dist/*.whl 2>/dev/null | wc -l)
        tar_count=$(ls dist/*.tar.gz 2>/dev/null | wc -l)
        
        if [ "$wheel_count" -gt 0 ] && [ "$tar_count" -gt 0 ]; then
            print_success "✓ 构建成功：包含wheel和源码包"
        else
            print_warning "⚠ 构建不完整：缺少wheel或源码包"
        fi
    else
        print_error "✗ 构建失败：dist目录不存在"
        exit 1
    fi
}

# 验证包安装
test_install() {
    print_info "测试包安装..."
    
    # 创建临时虚拟环境进行测试
    if command -v python -m venv &> /dev/null; then
        temp_env="temp_test_env"
        python -m venv "$temp_env"
        source "$temp_env/bin/activate" 2>/dev/null || source "$temp_env/Scripts/activate"
        
        # 安装构建的包
        pip install dist/*.whl
        
        # 测试导入
        python -c "import dlt645; print('包导入成功')"
        
        # 清理
        deactivate
        rm -rf "$temp_env"
        
        print_success "✓ 包安装测试通过"
    else
        print_warning "⚠ 跳过安装测试（venv不可用）"
    fi
}

# 显示安装说明
show_install_instructions() {
    print_info "\n安装说明："
    echo "本地安装："
    echo "  pip install dist/dlt645_protocol-1.0.0-py3-none-any.whl"
    echo ""
    echo "从源码安装："
    echo "  pip install dist/dlt645-protocol-1.0.0.tar.gz"
    echo ""
    echo "开发模式安装："
    echo "  pip install -e ."
    echo ""
    print_info "发布到PyPI（可选）："
    echo "  pip install twine"
    echo "  twine upload dist/*"
}

# 主函数
main() {
    print_info "DLT645协议包构建脚本"
    print_info "========================"
    
    check_directory
    
    # 解析命令行参数
    case "${1:-build}" in
        "clean")
            clean_build
            ;;
        "test")
            run_tests
            ;;
        "build")
            clean_build
            check_dependencies
            run_tests
            build_package
            check_build
            show_install_instructions
            ;;
        "quick")
            clean_build
            build_package
            check_build
            ;;
        "all")
            clean_build
            check_dependencies
            run_tests
            build_package
            check_build
            test_install
            show_install_instructions
            ;;
        *)
            print_info "用法: $0 [clean|test|build|quick|all]"
            print_info "  clean  - 清理构建文件"
            print_info "  test   - 运行测试"
            print_info "  build  - 完整构建（默认）"
            print_info "  quick  - 快速构建（跳过测试）"
            print_info "  all    - 完整构建+测试安装"
            exit 1
            ;;
    esac
    
    print_success "\n✓ 操作完成！"
}

# 运行主函数
main "$@"