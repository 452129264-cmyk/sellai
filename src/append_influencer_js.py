#!/usr/bin/env python3
"""
将达人洽谈面板JavaScript添加到HTML文件
"""

import sys
import os

def append_js():
    input_file = "outputs/仪表盘/SellAI_办公室_达人洽谈版.html"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 读取JavaScript文件
    js_file = "src/influencer_panel.js"
    with open(js_file, 'r', encoding='utf-8') as f:
        js_content = f.read()
    
    # 在</body>标签前插入新的script标签
    # 先检查是否已经存在相关script
    if 'InfluencerPanelManager' in content:
        print('达人洽谈面板JavaScript已存在')
        return True
    
    # 插入位置：在最后一个</script>标签之后，</body>之前
    # 但更好的做法是直接在</body>之前插入
    marker = '</body>'
    
    if marker in content:
        # 构建新的script标签
        new_script = f'\n    <!-- 达人洽谈面板JavaScript -->\n    <script>\n{js_content}\n    </script>\n\n    {marker}'
        
        # 替换marker
        new_content = content.replace(marker, new_script)
        
        with open(input_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f'达人洽谈面板JavaScript已添加到: {input_file}')
        return True
    else:
        print(f'未找到{marker}标记')
        return False

if __name__ == "__main__":
    success = append_js()
    sys.exit(0 if success else 1)