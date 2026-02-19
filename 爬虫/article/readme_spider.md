# 🕷️ SMSF文章爬虫框架

## 📋 项目概述

这是一个专业的英文文章爬虫框架，专门用于从AEON等网站抓取高质量文章内容，支持自动化数据清洗、翻译和数据库存储。

## 🏗️ 项目架构

```
article/
├── one.py          # 核心爬虫模块
├── 抓新.py         # 增量爬虫调度器
├── ai加工.py       # AI翻译处理模块
├── db_importer.py  # 数据库导入工具
├── all_res.txt     # 已处理文章记录
└── readme_spider.md # 本文档
```

## 🚀 功能特性

### 🔧 核心功能
- **智能网页抓取**: 自动提取文章标题、作者、日期和正文内容
- **数据清洗**: 专业级HTML内容清洗，去除广告和无关信息
- **AI翻译**: 集成腾讯云翻译API，支持英中互译
- **数据库集成**: 自动导入清洗后的数据到MySQL数据库
- **增量更新**: 智能识别新文章，避免重复抓取
- **封面图片**: 自动下载并保存文章封面图片

### 🛡️ 安全特性
- 敏感信息已清理（API密钥、数据库配置等）
- 使用环境变量管理配置
- 空配置占位符，便于安全部署

## 📦 模块详解

### 1. one.py - 核心爬虫模块
```python
def one_main(url):
    """主爬虫函数"""
    # 抓取网页内容
    # 提取文章信息
    # 清洗HTML内容
    # 保存结构化数据
    # 下载封面图片
```

**主要功能**:
- 网页内容抓取和解析
- 文章元数据提取
- 专业HTML内容清洗
- 封面图片自动下载
- 数据结构化保存

### 2. 抓新.py - 批量调度器
```python
# 自动发现新文章
# 批量处理未抓取内容
# 调用各模块协同工作
```

**主要功能**:
- 批量文章发现和去重
- 自动化处理流程调度
- 错误处理和重试机制
- 处理进度监控

### 3. ai加工.py - AI翻译模块
```python
class TencentTranslator:
    """腾讯云翻译API封装"""
    
class TranslationProcessor:
    """翻译处理器"""
```

**主要功能**:
- 腾讯云翻译API集成
- 批量文本翻译
- 翻译结果数据库更新
- 翻译质量监控

### 4. db_importer.py - 数据库工具
```python
class ArticleDatabaseImporter:
    """文章数据库导入器"""
```

**主要功能**:
- 数据库连接管理
- 文章数据结构化解析
- 批量数据导入
- 数据库状态监控

## ⚙️ 配置说明

### 环境变量配置
```bash
# 腾讯云API密钥
export TENCENTCLOUD_SECRET_ID="your_secret_id"
export TENCENTCLOUD_SECRET_KEY="your_secret_key"

# MySQL数据库配置
export DB_HOST="your_host"
export DB_USER="your_user" 
export DB_PASSWORD="your_password"
export DB_NAME="your_database"
```

### 配置文件示例
```python
# 在各模块中配置实际参数
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4'
}
```

## 🚀 使用指南

### 1. 基础使用
```python
# 单篇文章抓取
from one import one_main
one_main("https://aeon.co/essays/article-url")

# 批量更新
from 抓新 import *
# 自动执行批量处理流程
```

### 2. 数据导入
```python
# 导入数据库
from db_importer import demo_usage
demo_usage()

# AI翻译处理
from ai加工 import demo_usage_ai
demo_usage_ai()
```

### 3. 文件清理
```python
# 清理临时文件
cleanup_txt_files()
```

## 📊 数据流程

```
1. URL输入 → 2. 网页抓取 → 3. 内容解析 → 4. 数据清洗 
     ↓           ↓           ↓           ↓
5. 结构化保存 → 6. 封面下载 → 7. 数据库存储 → 8. AI翻译
```

## 🔧 技术栈

- **Python**: 3.8+
- **Requests**: 网页抓取
- **Regular Expressions**: 内容提取
- **腾讯云API**: AI翻译服务
- **PyMySQL**: MySQL数据库操作
- **HTML Processing**: 专业内容清洗

## 📈 性能优化

- **并发控制**: 合理的请求间隔避免被封IP
- **内存管理**: 及时释放不需要的对象
- **错误重试**: 网络异常自动重试机制
- **增量处理**: 智能识别避免重复工作

## 🛡️ 安全注意事项

1. **API密钥**: 请在生产环境中使用环境变量配置
2. **频率限制**: 遵守目标网站的robots.txt规则
3. **数据合规**: 确保抓取内容符合版权法规
4. **隐私保护**: 不存储用户敏感信息

## 🐛 常见问题

### Q: 抓取失败怎么办？
A: 检查网络连接，确认URL有效性，查看错误日志

### Q: 翻译质量不佳？
A: 可调整翻译参数，或使用专业术语词典

### Q: 数据库连接失败？
A: 确认数据库配置正确，检查网络和权限设置

### Q: 封面图片下载失败？
A: 检查图片URL有效性，确认目标目录权限

## 📝 维护建议

- 定期更新依赖库版本
- 监控API使用额度
- 备份重要数据文件
- 记录处理日志便于排查问题

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个框架！

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

---
*最后更新: 2026年2月*