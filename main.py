#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻日报机器人主程序
每日自动聚合AI相关新闻并推送到钉钉
"""

import json
import logging
import requests
import feedparser
import hmac
import hashlib
import time
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_news_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class NewsItem:
    """新闻条目数据结构"""
    
    def __init__(self, title: str, summary: str, url: str, source: str, 
                 published: datetime, category: str, importance_score: float = 0.0):
        self.title = title
        self.summary = summary
        self.url = url
        self.source = source
        self.published = published
        self.category = category
        self.importance_score = importance_score


class NewsAggregator:
    """新闻聚合器"""
    
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.webhook_url = self.config["dingtalk_webhook"]
        self.secret = self.config.get("dingtalk_secret", "")
        self.sent_urls_file = "sent_urls.json"
        self.sent_urls = self._load_sent_urls()
        
    def _load_sent_urls(self) -> set:
        """加载已发送的新闻URL"""
        try:
            with open(self.sent_urls_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('sent_urls', []))
        except FileNotFoundError:
            return set()
    
    def _save_sent_urls(self):
        """保存已发送的新闻URL"""
        data = {
            'sent_urls': list(self.sent_urls),
            'last_update': datetime.now().isoformat()
        }
        with open(self.sent_urls_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_url_hash(self, url: str) -> str:
        """生成URL的哈希值用于去重"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _is_duplicate(self, url: str) -> bool:
        """检查是否重复新闻"""
        url_hash = self._get_url_hash(url)
        return url_hash in self.sent_urls
    
    def _calculate_importance_score(self, title: str, keywords: List[str]) -> float:
        """计算新闻重要性评分"""
        score = 0.0
        title_lower = title.lower()
        
        # 基础分数
        score += 1.0
        
        # 关键词匹配加分
        for keyword in keywords:
            if keyword.lower() in title_lower:
                score += 2.0
        
        # 特殊关键词额外加分
        high_value_keywords = [
            'openai', 'gpt-4', 'claude', 'anthropic', 'funding', 'acquisition',
            'breakthrough', 'research', 'paper'
        ]
        for keyword in high_value_keywords:
            if keyword in title_lower:
                score += 3.0
        
        return score
    
    def _fetch_rss_feed(self, source: Dict) -> List[NewsItem]:
        """抓取RSS源"""
        try:
            logger.info("正在抓取: " + source['name'])
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(source['url'], headers=headers, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            news_items = []
            
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for entry in feed.entries[:50]:
                try:
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    
                    if published < cutoff_time:
                        continue
                    
                    title = getattr(entry, 'title', '').strip()
                    url = getattr(entry, 'link', '').strip()
                    
                    if not title or not url:
                        continue
                    
                    if self._is_duplicate(url):
                        continue
                    
                    importance_score = self._calculate_importance_score(
                        title, source.get('keywords', [])
                    )
                    
                    summary = getattr(entry, 'summary', '')
                    if not summary and hasattr(entry, 'description'):
                        summary = getattr(entry, 'description', '')
                    
                    summary = self._clean_html(summary)
                    
                    news_item = NewsItem(
                        title=title,
                        summary=summary[:200] + "..." if len(summary) > 200 else summary,
                        url=url,
                        source=source['name'],
                        published=published,
                        category=source.get('category', 'general'),
                        importance_score=importance_score
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    logger.warning("处理新闻条目时出错: " + str(e))
                    continue
            
            logger.info("从 " + source['name'] + " 抓取到 " + str(len(news_items)) + " 条新闻")
            return news_items
            
        except Exception as e:
            logger.error("抓取 RSS 源失败 " + source['name'] + ": " + str(e))
            return []
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def fetch_all_news(self) -> List[NewsItem]:
        """抓取所有新闻源"""
        all_news = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {}
            
            for category, sources in self.config["news_sources"].items():
                for source in sources:
                    source['category'] = category
                    future = executor.submit(self._fetch_rss_feed, source)
                    future_to_source[future] = source
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    news_items = future.result()
                    all_news.extend(news_items)
                except Exception as e:
                    logger.error("获取新闻时出错 " + source['name'] + ": " + str(e))
        
        all_news.sort(key=lambda x: x.importance_score, reverse=True)
        
        logger.info("总共抓取到 " + str(len(all_news)) + " 条新闻")
        return all_news


class AISummarizer:
    """AI新闻摘要器"""
    
    def __init__(self, config: Dict):
        self.api_key = config["ai_summary"]["api_key"]
        self.model = config["ai_summary"]["model"]
        self.max_tokens = config["ai_summary"]["max_tokens"]
        self.temperature = config["ai_summary"]["temperature"]
        
    def generate_summary(self, news_item: NewsItem) -> str:
        """使用AI生成新闻摘要"""
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY":
            return news_item.summary or "暂无摘要"
        
        try:
            prompt = "请为以下AI相关新闻生成一个简洁的中文摘要，要求：\n"
            prompt += "1. 长度控制在50字以内\n"
            prompt += "2. 保留关键信息（公司名、技术名、数据等）\n"
            prompt += "3. 语言客观专业\n\n"
            prompt += "新闻标题：" + news_item.title + "\n"
            prompt += "新闻内容：" + news_item.summary + "\n\n"
            prompt += "请直接输出摘要，不需要其他说明。"
            
            headers = {
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
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
                return result["choices"][0]["message"]["content"].strip()
            else:
                return news_item.summary or "暂无摘要"
                
        except Exception as e:
            logger.error("AI摘要生成失败: " + str(e))
            return news_item.summary or "暂无摘要"


class DingTalkNotifier:
    """钉钉通知器"""
    
    def __init__(self, webhook_url: str, secret: str = ""):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _get_sign(self) -> str:
        """生成签名（如果配置了secret）"""
        if not self.secret:
            return ""
        
        timestamp = str(int(time.time() * 1000))
        string_to_sign = timestamp + "\n" + self.secret
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return "&timestamp=" + timestamp + "&sign=" + sign
    
    def send_daily_news(self, news_items: List[NewsItem], date: str) -> bool:
        """发送每日新闻"""
        try:
            message = self._build_markdown_message(news_items, date)
            
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "AI每日早报 | " + date,
                    "text": message
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            url = self.webhook_url
            if self.secret:
                url += self._get_sign()
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info("钉钉消息发送成功")
                return True
            else:
                logger.error("钉钉消息发送失败: " + result.get('errmsg'))
                return False
            
        except Exception as e:
            logger.error("钉钉消息发送失败: " + str(e))
            return False
    
    def _build_markdown_message(self, news_items: List[NewsItem], date: str) -> str:
        """构建Markdown格式的消息"""
        message_parts = []
        
        message_parts.append("## 📅 AI 每日早报 | " + date)
        message_parts.append("")
        message_parts.append("**今日精选 " + str(len(news_items)) + " 条AI要闻**")
        message_parts.append("")
        
        for i, news in enumerate(news_items, 1):
            emoji = self._get_category_emoji(news.category)
            
            news_line = "**" + emoji + " " + news.title + "**\n"
            news_line += "> " + news.summary + "\n"
            news_line += "> 📰 来源：" + news.source + "\n"
            news_line += "> 🔗 [原文链接](" + news.url + ")\n"
            
            message_parts.append(news_line)
        
        message_parts.append("")
        message_parts.append("---")
        message_parts.append("*本简报由 AI 自动生成，仅供内部参考*")
        
        return "\n".join(message_parts)
    
    def _get_category_emoji(self, category: str) -> str:
        """根据类别返回对应的emoji"""
        emoji_map = {
            "international_media": "🌍",
            "chinese_media": "🇨🇳", 
            "ai_funding": "💰",
            "general": "📰"
        }
        return emoji_map.get(category, "📰")


class AINewsBot:
    """AI新闻机器人主类"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.aggregator = NewsAggregator(config_path)
        self.summarizer = AISummarizer(self.aggregator.config)
        self.notifier = DingTalkNotifier(
            self.aggregator.webhook_url,
            self.aggregator.secret
        )
    
    def run_daily_job(self) -> bool:
        """执行每日新闻收集和推送任务"""
        try:
            logger.info("开始执行每日新闻任务")
            
            all_news = self.aggregator.fetch_all_news()
            
            if not all_news:
                logger.warning("未抓取到任何新闻")
                return False
            
            max_news = self.aggregator.config["settings"]["max_news"]
            selected_news = all_news[:max_news]
            
            logger.info("筛选出 " + str(len(selected_news)) + " 条高质量新闻")
            
            for news in selected_news:
                news.summary = self.summarizer.generate_summary(news)
                time.sleep(1)
            
            current_date = datetime.now().strftime("%Y年%m月%d日")
            success = self.notifier.send_daily_news(selected_news, current_date)
            
            if success:
                for news in selected_news:
                    self.aggregator.sent_urls.add(
                        self.aggregator._get_url_hash(news.url)
                    )
                self.aggregator._save_sent_urls()
                
                logger.info("每日新闻任务执行完成")
                return True
            else:
                logger.error("发送消息失败")
                return False
                
        except Exception as e:
            logger.error("执行每日任务时出错: " + str(e))
            return False


def main():
    """主函数"""
    try:
        bot = AINewsBot()
        success = bot.run_daily_job()
        
        if success:
            logger.info("程序执行成功")
            exit(0)
        else:
            logger.error("程序执行失败")
            exit(1)
            
    except Exception as e:
        logger.error("程序异常: " + str(e))
        exit(1)


if __name__ == "__main__":
    main()
