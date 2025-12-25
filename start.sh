#!/bin/bash

# AI新闻机器人启动脚本

echo "🚀 启动AI新闻日报机器人..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip3 install -r requirements.txt

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "❌ 配置文件 config.json 不存在"
    exit 1
fi

# 检查企业微信Webhook URL
if grep -q "YOUR_WECHAT_WEBHOOK_URL" config.json; then
    echo "⚠️  请在config.json中配置您的企业微信Webhook URL"
    echo "📖 详细配置说明请参考 README.md"
    exit 1
fi

# 创建必要目录
mkdir -p logs

# 运行程序
echo "✅ 环境检查完成，开始运行..."
python3 main.py

echo "🤖 AI新闻机器人运行完成"