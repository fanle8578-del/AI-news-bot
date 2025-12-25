#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI新闻日报机器人 - 钉钉版
每日自动聚合AI相关新闻并推送到钉钉
"""

import json
import logging
import requests
import feedparser
import time
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
    """新闻聚合器"""
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
    
    def _calculate_score(self, title, keywords):
        score = 1.0
        title_lower = title.lower()
        for kw in keywords:
            if kw.lower() in title_lower:
                score += 2.0
        for kw in ['openai', 'gpt', 'funding', 'research', 'breakthrough']:
            if kw in title_lower:
                score += 3.0
        return score
    
    def _fetch_rss(self, source):
        try:
            logger.info("正在抓取: " + source['name'])
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(source['url'], headers=headers, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            news_list = []
            cutoff = datetime.now() - timedelta(hours=24)
            
            for entry in feed.entries[:30]:
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
                    
                    import re
                    summary = getattr(entry, 'summary', '')
                    summary = re.sub(r'<[^>]+>', '', summary)
                    summary = re.sub(r'\s+', ' ', summary).strip()[:200]
                    
                    news = NewsItem(
                        title=title,
                        summary=summary + "...",
                        url=url,
                        source=source['name'],
                        published=published,
                        category=source.get('category', 'general'),
                        importance_score=self._calculate_score(title, source.get('keywords', []))
                    )
                    news_list.append(news)
                except Exception as e:
                    continue
            
            logger.info("从 " + source['name'] + " 抓取到 " + str(len(news_list)) + " 条新闻")
            return news_list
        except Exception as e:
            logger.error("抓取失败 " + source['name'] + ": " + str(e))
            return []
    
    def fetch_all(self):
        all_news = []
        with ThreadPoolExecutor(max_workers=3) as executor:
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
        
        all_news.sort(key=lambda x: x.importance_score, reverse=True)
        logger.info("总共抓取到 " + str(len(all_news)) + " 条新闻")
        return all_news


class DingTalkSender:
    """钉钉发送器"""
    def __init__(self, webhook_url, secret=""):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _sign(self):
        """生成签名"""
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
            # 构建Markdown消息
            text = self._build_message(news_list, date_str)
            
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "AI每日早报 | " + date_str,
                    "text": text
                }
            }
            
            url = self.webhook_url + self._sign()
            
            headers = {"Content-Type": "application/json"}
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("钉钉消息发送成功")
                return True
            else:
                logger.error("钉钉发送失败: " + str(result))
                # 如果加签失败，尝试不使用签名
                if "签名不匹配" in str(result.get("errmsg", "")):
                    logger.info("尝试不使用签名重新发送...")
                    response = requests.post(self.webhook_url, json=payload, headers=headers, timeout=30)
                    result = response.json()
                    if result.get("errcode") == 0:
                        logger.info("不使用签名发送成功")
                        return True
                return False
                
        except Exception as e:
            logger.error("发送异常: " + str(e))
            return False
    
    def _build_message(self, news_list, date_str):
        lines = []
        lines.append("## 📅 AI 每日早报 | " + date_str)
        lines.append("")
        lines.append("**今日精选 " + str(len(news_list)) + " 条AI要闻**")
        lines.append("")
        
        for i, news in enumerate(news_list, 1):
            emoji_map = {"international_media": "🌍", "chinese_media": "🇨🇳", "ai_funding": "💰"}
            emoji = emoji_map.get(news.category, "📰")
            
            lines.append("**" + emoji + " " + news.title + "**")
            lines.append("> " + news.summary)
            lines.append("> 📰 " + news.source + " | [🔗原文](" + news.url + ")")
            lines.append("")
        
        lines.append("---")
        lines.append("*本简报由 AI 自动生成*")
        
        return "\n".join(lines)


class AINewsBot:
    """主机器人"""
    def __init__(self):
        self.aggregator = NewsAggregator()
        self.sender = DingTalkSender(self.aggregator.webhook_url, self.aggregator.secret)
    
    def run(self):
        try:
            logger.info("开始执行每日新闻任务")
            
            all_news = self.aggregator.fetch_all()
            if not all_news:
                logger.warning("未抓取到任何新闻")
                return False
            
            max_news = self.aggregator.config["settings"]["max_news"]
            selected = all_news[:max_news]
            logger.info("筛选出 " + str(len(selected)) + " 条高质量新闻")
            
            date_str = datetime.now().strftime("%Y年%m月%d日")
            success = self.sender.send(selected, date_str)
            
            if success:
                for news in selected:
                    self.aggregator.sent_urls.add(self.aggregator._get_url_hash(news.url))
                self.aggregator._save_sent_urls()
                logger.info("任务执行完成")
                return True
            else:
                logger.error("发送消息失败")
                return False
                
        except Exception as e:
            logger.error("执行异常: " + str(e))
            return False


def main():
    bot = AINewsBot()
    success = bot.run()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
