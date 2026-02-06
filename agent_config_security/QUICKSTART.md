# 快速开始指南

## 安装

```bash
# 克隆或复制 agent_config_security 目录
cd agent_config_security

# 安装依赖
pip install -r requirements.txt
```

## 基础用法

### 1. 环境变量模式 (最简单)

```python
from config import SecureConfigLoader

# 初始化 (从环境变量加载)
config = SecureConfigLoader(vault_uri="env://AGENT_")

# 获取配置
api_key = config.get_secret("openai_api_key")
db_host = config.get("database_host", default="localhost")
```

### 2. 使用 Pydantic 模型

```python
from config.loader import AgentConfig

# 自动验证和类型转换
config = SecureConfigLoader(vault_uri="env://AGENT_")
agent_config = config.load_model(AgentConfig)

print(agent_config.database.host)
print(agent_config.api.base_url)
```

### 3. 临时凭证

```python
from config import SandboxInjector

injector = SandboxInjector(ttl_seconds=300)

# 创建临时凭证
cred = injector.create_credential("api_key", "sk-...", ttl_seconds=60)

# 在作用域内使用 (自动清理)
with injector.inject_context("API_KEY", "sk-..."):
    # API_KEY 已注入到环境
    call_api()

# 自动清理
```

### 4. 日志脱敏

```python
from security import setup_logging_with_sanitization

# 设置自动脱敏的日志
setup_logging_with_sanitization()

import logging
logger = logging.getLogger(__name__)

# 自动脱敏
logger.info({"api_key": "sk-1234567890"})  # 输出: sk-***1234
```

## 环境变量配置

```bash
# Vault 配置
export AGENT_VAULT_URI="env://AGENT_"           # 使用环境变量
export AGENT_VAULT_URI="file://secrets/vault.enc"  # 使用加密文件
export AGENT_VAULT_URI="aws://us-east-1"        # 使用 AWS Secrets Manager

# 加密密钥 (文件模式需要)
export AGENT_MASTER_KEY="$(openssl rand -hex 32)"

# 审计日志
export AUDIT_SIGNING_KEY="$(openssl rand -hex 32)"
```

## 生产环境设置

```bash
# 运行设置向导
python examples/production_setup.py

# 运行安全检查
python -m pytest tests/ -v
```
