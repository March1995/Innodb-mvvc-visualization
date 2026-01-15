#!/bin/bash

# InnoDB MVCC 可视化系统 - 快速验证和启动脚本

echo "================================================================="
echo "  InnoDB MVCC 可视化系统 v2.0 - 快速验证和启动"
echo "================================================================="
echo ""

# 检查 Python 版本
echo "1. 检查 Python 版本..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ 错误: 未找到 Python 3"
    exit 1
fi
echo "✅ Python 3 已安装"
echo ""

# 检查 Flask
echo "2. 检查 Flask..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Flask 未安装，正在安装..."
    pip install flask
    if [ $? -ne 0 ]; then
        echo "❌ 错误: Flask 安装失败"
        exit 1
    fi
fi
echo "✅ Flask 已安装"
echo ""

# 运行完整验证
echo "3. 运行完整验证..."
echo "================================================================="
python3 verify_all.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 验证失败，请检查错误信息"
    exit 1
fi
echo ""

# 询问是否启动系统
echo "================================================================="
echo "✅ 所有验证通过！"
echo ""
echo "是否启动系统？(y/n)"
read -r response

if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    echo ""
    echo "正在启动系统..."
    echo "================================================================="
    echo "访问地址: http://127.0.0.1:5001"
    echo "按 Ctrl+C 停止服务器"
    echo "================================================================="
    echo ""
    python3 app.py
else
    echo ""
    echo "使用说明："
    echo "  1. 运行测试: python3 test_mvcc.py"
    echo "  2. 运行演示: python3 demo_scenarios.py"
    echo "  3. 启动系统: python3 app.py"
    echo "  4. 查看文档: cat FINAL_GUIDE.md"
    echo ""
fi
