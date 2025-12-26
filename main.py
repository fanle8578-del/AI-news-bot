#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻日报机器人 - 优化版
聚焦：世界模型、AI算力、头部公司动态、融资资讯
"""

import json
import logging
import requests
import feedparser
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsItem:
    """新闻条目"""
    def __init__(self, title, summary, url, source, published, category, importance_score=0.0):
        self.title = title
        self.summary = summary
        self.url = url
        self.source = source
        self.published = published
        self.category = category
        self.importance_score = importance_score


class NewsAggregator:
    """新闻聚合器 - 聚焦版"""
    def __init__(self, config_path="config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.webhook_url = self.config["dingtalk_webhook"]
        self.secret = self.config.get("dingtalk_secret", "")
        self.sent_urls = self._load_sent_urls()
        
    def _load_sent_urls(self):
        try:
            with open("sent_urls.json", 'r', encoding='utf-8') as f:
                return set(json.load(f).get('sent_urls', []))
        except:
            return set()
    
    def _save_sent_urls(self):
        with open("sent_urls.json", 'w', encoding='utf-8') as f:
            json.dump({"sent_urls": list(self.sent_urls)}, f)
    
    def _get_url_hash(self, url):
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_duplicate(self, url):
        return self._get_url_hash(url) in self.sent_urls
    
    def _calculate_score(self, title):
        """计算新闻重要性评分 - 聚焦领域加权"""
        score = 1.0
        title_lower = title.lower()
        
        # 高权重关键词（头部AI公司）
        high_weight = ['openai', 'anthropic', 'google deepmind', 'meta ai', 'claude', 'gpt-5', 'gpt-4', 'sora', 'gemini']
        for kw in high_weight:
            if kw in title_lower:
                score += 5.0
        
        # 中权重关键词（核心领域）
        mid_weight = ['world model', 'world model', 'AI compute', 'AI chips', 'GPU', 'Nvidia', 'funding', 'Series A', 'Series B', 'Series C', 'data annotation', 'human labeling', 'AI startup']
        for kw in mid_weight:
            if kw in title_lower:
                score += 3.0
        
        # 一般权重关键词
        general = ['generative AI', 'LLM', 'multimodal', 'AI infrastructure', 'AI investment']
        for kw in general:
            if kw in title_lower:
                score += 1.5
        
        return score
    
    def _fetch_rss(self, source):
        try:
            logger.info("正在抓取: " + source['name'])
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(source['url'], headers=headers, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            news_list = []
            cutoff = datetime.now() - timedelta(hours=24)
            
            for entry in feed.entries[:50]:
                try:
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    
                    if published < cutoff:
                        continue
                    
                    title = getattr(entry, 'title', '').strip()
                    url = getattr(entry, 'link', '').strip()
                    
                    if not title or not url or self._is_duplicate(url):
                        continue
                    
                    # 计算重要性
                    importance = self._calculate_score(title)
                    
                    # 生成摘要
                    summary = getattr(entry, 'summary', '')
                    summary = re.sub(r'<[^>]+>', '', summary)
                    summary = re.sub(r'\s+', ' ', summary).strip()[:250]
                    
                    news = NewsItem(
                        title=title,
                        summary=summary + "...",
                        url=url,
                        source=source['name'],
                        published=published,
                        category=source.get('category', 'general'),
                        importance_score=importance
                    )
                    news_list.append(news)
                except Exception as e:
                    continue
            
            logger.info("从 " + source['name'] + " 抓取到 " + str(len(news_list)) + " 条相关新闻")
            return news_list
        except Exception as e:
            logger.error("抓取失败 " + source['name'] + ": " + str(e))
            return []
    
    def fetch_all(self):
        all_news = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for category, sources in self.config["news_sources"].items():
                for src in sources:
                    src['category'] = category
                    futures.append(executor.submit(self._fetch_rss, src))
            
            for f in futures:
                try:
                    all_news.extend(f.result())
                except:
                    pass
        
        # 按重要性排序
        all_news.sort(key=lambda x: x.importance_score, reverse=True)
        logger.info("总共筛选出 " + str(len(all_news)) + " 条高质量新闻")
        return all_news


class DingTalkSender:
    """钉钉发送器 - UI优化版"""
    def __init__(self, webhook_url, secret=""):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _sign(self):
        if not self.secret:
            return ""
        
        timestamp = str(int(time.time() * 1000))
        string = timestamp + "\n" + self.secret
        
        import hmac
        import base64
        import hashlib
        
        signature = hmac.new(
            self.secret.encode('utf-8'),
            string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = base64.b64encode(signature).decode('utf-8')
        return "&timestamp=" + timestamp + "&sign=" + sign
    
    def send(self, news_list, date_str):
        try:
            text = self._build_message(news_list, date_str)
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "🤖 AI Daily Brief | " + date_str,
                    "text": text
                }
            }
            
            url = self.webhook_url + self._sign()
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("✅ 钉钉消息发送成功")
                return True
            else:
                logger.error("❌ 钉钉发送失败: " + str(result))
                return False
                
        except Exception as e:
            logger.error("❌ 发送异常: " + str(e))
            return False
    
    def _build_message(self, news_list, date_str):
        """构建优化后的UI界面"""
        lines = []
        
        # 🎯 标题区域
        lines.append("## 🤖 AI Daily Brief")
        lines.append("### 📅 " + date_str)
        lines.append("")
        
        # 📊 统计信息
        lines.append("---")
        lines.append("📈 **今日精选 " + str(len(news_list)) + " 条核心资讯**")
        lines.append("")
        
        # 按类别分组统计
        categories = {}
        for news in news_list:
            cat = news.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(news)
        
        # 类别emoji映射
        emoji_map = {
            "ai_research": "🔬",
            "ai_funding": "💰", 
            "ai_compute": "⚡",
            "ai_data": "📊",
            "ai_product": "🚀",
            "general": "📰"
        }
        
        category_names = {
            "ai_research": "头部公司研发",
            "ai_funding": "融资动态",
            "ai_compute": "算力市场",
            "ai_data": "数据标注",
            "ai_product": "AI应用",
            "general": "综合资讯"
        }
        
        # 显示各类别统计
        stats_parts = []
        for cat, cat_news in categories.items():
            emoji = emoji_map.get(cat, "📰")
            name = category_names.get(cat, "综合资讯")
            stats_parts.append(emoji + " " + name + ": " + str(len(cat_news)))
        
        lines.append(" | ".join(stats_parts))
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 📰 新闻详情
        lines.append("### 📰 **今日要闻**")
        lines.append("")
        
        for i, news in enumerate(news_list, 1):
            emoji = emoji_map.get(news.category, "📰")
            
            # 标题（加粗）
            lines.append("#### " + emoji + " **" + news.title + "**")
            
            # 摘要（引用格式）
            lines.append("> " + news.summary)
            
            # 来源和链接
            lines.append("> 📍 **" + news.source + "** | 🔗 [阅读原文](" + news.url + ")")
            lines.append("")
        
        # 🎯 底部信息
        lines.append("---")
        lines.append("")
        lines.append("💡 **聚焦领域**: 世界模型 | AI算力 | 数据标注 | 头部公司动态 | 融资资讯")
        lines.append("")
        lines.append("🤖 *本简报由 AI 自动生成，每日09:30定时推送*")
        
        return "\n".join(lines)


class AINewsBot:
    """主机器人 - 优化版"""
    def __init__(self):
        self.aggregator = NewsAggregator()
        self.sender = DingTalkSender(self.aggregator.webhook_url, self.aggregator.secret)
    
    def run(self):
        try:
            logger.info("🚀 开始执行AI新闻任务")
            logger.info("=" * 50)
            
            # 抓取新闻
            all_news = self.aggregator.fetch_all()
            
            if not all_news:
                logger.warning("⚠️ 未抓取到任何新闻")
                return False
            
            # 筛选top 10
            max_news = self.aggregator.config["settings"]["max_news"]
            selected = all_news[:max_news]
            
            logger.info("✅ 筛选出 " + str(len(selected)) + " 条核心资讯")
            logger.info("=" * 50)
            
            # 发送
            date_str = datetime.now().strftime("%Y.%m.%d")
            success = self.sender.send(selected, date_str)
            
            if success:
                for news in selected:
                    self.aggregator.sent_urls.add(self.aggregator._get_url_hash(news.url))
                self.aggregator._save_sent_urls()
                logger.info("🎉 任务执行完成！")
                return True
            else:
                logger.error("❌ 发送消息失败")
                return False
                
        except Exception as e:
            logger.error("❌ 执行异常: " + str(e))
            return False


def main():
    bot = AINewsBot()
    success = bot.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
