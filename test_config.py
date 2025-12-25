#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻机器人配置测试脚本
用于验证各项配置是否正确
"""

import json
import requests
import feedparser
from datetime import datetime

def test_config():
    """测试配置文件"""
    print("🔧 测试配置文件...")
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # 检查必要字段
        required_fields = ["wechat_webhook", "news_sources", "settings"]
        for field in required_fields:
            if field not in config:
                print(f"❌ 缺少必要字段: {field}")
                return False
        
        print("✅ 配置文件格式正确")
        return True
        
    except FileNotFoundError:
        print("❌ 配置文件 config.json 不存在")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        return False

def test_wechat_webhook(webhook_url):
    """测试企业微信Webhook"""
    print("\n📱 测试企业微信Webhook...")
    
    if webhook_url == "YOUR_WECHAT_WEBHOOK_URL":
        print("⚠️  请在config.json中配置您的企业微信Webhook URL")
        return False
    
    try:
        # 发送测试消息
        test_data = {
            "msgtype": "text",
            "text": {
                "content": f"🤖 AI新闻机器人配置测试\n⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n✅ 配置测试成功！"
            }
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(webhook_url, headers=headers, json=test_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("errcode") == 0:
                print("✅ 企业微信Webhook配置正确，测试消息发送成功")
                return True
            else:
                print(f"❌ 企业微信API返回错误: {result}")
                return False
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 企业微信Webhook测试失败: {e}")
        return False

def test_news_sources():
    """测试新闻源"""
    print("\n📰 测试新闻源...")
    
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        
        sources = config.get("news_sources", {})
        total_sources = 0
        working_sources = 0
        
        for category, source_list in sources.items():
            print(f"\n📊 测试 {category} 类别:")
            
            for source in source_list:
                total_sources += 1
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    response = requests.get(source["url"], headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # 尝试解析RSS
                    feed = feedparser.parse(response.content)
                    if feed.bozo == 0 and len(feed.entries) > 0:
                        print(f"  ✅ {source['name']}: 正常 ({len(feed.entries)} 条新闻)")
                        working_sources += 1
                    else:
                        print(f"  ❌ {source['name']}: RSS解析失败")
                        
                except Exception as e:
                    print(f"  ❌ {source['name']}: 连接失败 - {str(e)[:50]}...")
        
        print(f"\n📈 新闻源测试完成: {working_sources}/{total_sources} 个源正常")
        return working_sources > 0
        
    except Exception as e:
        print(f"❌ 新闻源测试失败: {e}")
        return False

def test_ai_api(api_key):
    """测试AI API"""
    print("\n🤖 测试AI摘要API...")
    
    if not api_key or api_key == "YOUR_OPENAI_API_KEY":
        print("⚠️  未配置OpenAI API密钥，将使用原始摘要模式")
        return True
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": "测试消息：你好"}
            ],
            "max_tokens": 10
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        if "choices" in result and result["choices"]:
            print("✅ OpenAI API配置正确")
            return True
        else:
            print("❌ OpenAI API响应格式异常")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 AI新闻机器人配置测试")
    print("=" * 50)
    
    # 加载配置
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except:
        print("❌ 无法加载配置文件")
        return
    
    tests = []
    
    # 测试配置
    tests.append(test_config())
    
    # 测试企业微信
    webhook_url = config.get("wechat_webhook", "")
    tests.append(test_wechat_webhook(webhook_url))
    
    # 测试新闻源
    tests.append(test_news_sources())
    
    # 测试AI API
    ai_config = config.get("ai_summary", {})
    api_key = ai_config.get("api_key", "")
    tests.append(test_ai_api(api_key))
    
    # 总结
    print("\n" + "=" * 50)
    print("📋 测试结果汇总:")
    
    if all(tests):
        print("🎉 所有测试通过！您的AI新闻机器人配置正确。")
        print("💡 建议立即运行 'python main.py' 开始收集新闻")
    else:
        print("⚠️  部分测试失败，请检查上述错误信息并修复配置")
    
    print(f"\n📊 测试通过率: {sum(tests)}/{len(tests)} ({sum(tests)/len(tests)*100:.1f}%)")

if __name__ == "__main__":
    main()