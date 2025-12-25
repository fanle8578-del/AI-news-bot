---
AIGC:
    ContentProducer: Minimax Agent AI
    ContentPropagator: Minimax Agent AI
    Label: AIGC
    ProduceID: 3f667a327eabd0a44b7d0783de3e8a33
    PropagateID: 3f667a327eabd0a44b7d0783de3e8a33
    ReservedCode1: 3046022100f64ab571f316c043b4dd4ff988c8cd8adaa4678d88e5136ed8854b52b6061a170221008dc3c1e60e9a84a869f8044e9c446c4bce92126c0d4dedfbd68067cf1a1c36f2
    ReservedCode2: 30440220065a053f5f9bc7173b99f8d184bcdc3b1ea0def27bb42a87c2857bab3535b70d02202ebad65eddfc33b349da1f1ee5e16497362fcb960eb9a942b3dee3f3177d94e7
---

# 🚀 AI新闻机器人快速部署指南

## 📋 部署前准备

### 1. 企业微信机器人设置（5分钟）

1. **创建群聊**
   - 在企业微信中创建一个新群聊（至少需要2人）
   - 群名称可以设置为"AI新闻订阅群"

2. **添加自定义机器人**
   - 点击群聊右上角"..."菜单
   - 选择"添加群机器人"
   - 点击"自定义"
   - 设置机器人名称："AI新闻机器人"
   - 上传机器人头像（可选）

3. **获取Webhook URL**
   - 机器人创建成功后，点击群成员列表中的机器人
   - 复制Webhook地址，格式类似：
     ```
     https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
     ```

### 2. GitHub仓库准备（3分钟）

1. **Fork或创建仓库**
   ```bash
   # 方式1：直接下载代码到本地
   git clone https://github.com/your-username/ai-news-bot.git
   cd ai-news-bot
   
   # 方式2：在GitHub上创建新仓库后推送
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/ai-news-bot.git
   git push -u origin main
   ```

## 🔧 配置部署（10分钟）

### 方法一：GitHub Actions自动化部署（推荐）

1. **配置Secrets**
   进入GitHub仓库 → Settings → Secrets and variables → Actions → New repository secret：
   
   - `WECHAT_WEBHOOK_URL`: 粘贴您的企业微信Webhook地址
   - `OPENAI_API_KEY`: 您的OpenAI API密钥（可选）

2. **更新配置文件**
   ```bash
   # 编辑 config.json，替换默认配置
   nano config.json
   ```

3. **启用Actions**
   - 进入GitHub仓库的Actions页面
   - 找到"AI Daily News Bot"工作流
   - 点击"Enable workflow"

4. **测试运行**
   - 在Actions页面点击"Run workflow"
   - 查看执行日志确认无错误

### 方法二：Railway免费部署

1. **注册Railway账户**
   - 访问 https://railway.app
   - 使用GitHub账户登录

2. **部署项目**
   - 点击"New Project"
   - 选择"Deploy from GitHub repo"
   - 选择您的ai-news-bot仓库
   - Railway会自动检测Dockerfile

3. **设置环境变量**
   在Railway项目设置中添加：
   - `WECHAT_WEBHOOK_URL`: 您的企业微信Webhook地址
   - `OPENAI_API_KEY`: 您的OpenAI API密钥

4. **配置定时任务**
   ```bash
   # 在项目根目录创建 railway.toml
   echo '[build]
     builder = "dockerfile"' > railway.toml
   ```

## 🧪 本地测试（5分钟）

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置检查
```bash
python test_config.py
```

### 3. 手动运行
```bash
python main.py
```

## 📱 验证部署

### 检查企业微信
- 等待每日北京时间09:30自动发送
- 或手动触发测试发送

### 检查GitHub Actions
- 每日自动执行任务
- 在Actions页面查看执行日志

### 检查日志
```bash
# 查看本地日志
tail -f ai_news_bot.log

# 查看GitHub Actions日志
# 在仓库Actions页面查看
```

## 🛠️ 自定义配置

### 修改新闻源
```json
// 在 config.json 中添加自定义RSS源
{
  "name": "我的科技媒体",
  "url": "https://example.com/rss",
  "keywords": ["AI", "人工智能"],
  "category": "international_media"
}
```

### 调整发送时间
```yaml
# 在 .github/workflows/daily-news.yml 中修改
schedule:
  # 每天北京时间09:30执行
  - cron: '30 1 * * *'
```

### 修改新闻数量
```json
// 在 config.json 中修改
"settings": {
  "max_news": 15  // 改为15条新闻
}
```

## 🚨 故障排除

### 企业微信消息发送失败
- ✅ 检查Webhook URL是否正确
- ✅ 确认机器人状态正常
- ✅ 检查群聊是否仍有机器人

### 新闻抓取失败
- ✅ 检查网络连接
- ✅ 验证RSS源可访问性
- ✅ 查看日志文件

### GitHub Actions执行失败
- ✅ 检查Secrets配置
- ✅ 查看Actions执行日志
- ✅ 确认代码格式正确

## 📊 监控和维护

### 日常检查
- 每日查看GitHub Actions执行状态
- 监控企业微信消息接收情况
- 检查新闻源可用性

### 备份重要文件
- `config.json`: 配置文件
- `sent_urls.json`: 已发送记录
- 日志文件

### 定期更新
- 检查新的新闻源
- 更新依赖包版本
- 优化AI摘要提示词

## 🎯 成功指标

✅ **部署成功的标志**：
- 企业微信每日09:30收到新闻早报
- GitHub Actions显示"Success"状态
- 新闻内容质量和相关性良好

🎉 **恭喜！您的AI新闻机器人已成功部署！**

---
**需要帮助？** 查看完整的 [README.md](README.md) 或提交Issue