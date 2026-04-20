#!/bin/bash
# SellAI v3.2.0 自动化部署脚本

set -e

echo "=============================================="
echo "SellAI v3.2.0 自动化部署脚本"
echo "=============================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 步骤1: 安装依赖
echo -e "\n${GREEN}[1/5] 安装依赖...${NC}"
pip install -r requirements_complete.txt --quiet

# 步骤2: 检查模块状态
echo -e "\n${GREEN}[2/5] 检查模块状态...${NC}"
python3 check_modules.py

# 步骤3: 创建必要目录
echo -e "\n${GREEN}[3/5] 创建必要目录...${NC}"
mkdir -p data/shared_state
mkdir -p logs
mkdir -p outputs
echo "目录创建完成"

# 步骤4: 验证环境
echo -e "\n${GREEN}[4/5] 验证Python环境...${NC}"
python3 -c "
import sys
print(f'Python版本: {sys.version}')
print(f'工作目录: {__import__(\"os\").getcwd()}')

# 检查关键模块
modules = [
    'fastapi', 'uvicorn', 'pydantic', 'aiosqlite',
    'httpx', 'requests', 'pandas', 'numpy',
    'langchain', 'chromadb', 'schedule'
]
for m in modules:
    try:
        __import__(m)
        print(f'✓ {m}')
    except ImportError:
        print(f'✗ {m} - 需要安装')
"

# 步骤5: 启动服务
echo -e "\n${GREEN}[5/5] 准备启动...${NC}"
echo -e "
${GREEN}==============================================${NC}
${GREEN}部署完成！${NC}

启动命令:
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

访问地址:
  API文档: http://localhost:8000/docs
  健康检查: http://localhost:8000/health
  模块状态: http://localhost:8000/api/v3/modules

${GREEN}==============================================${NC}
"

# 启动服务（如果参数是start）
if [ "$1" = "start" ]; then
    echo "启动服务..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
