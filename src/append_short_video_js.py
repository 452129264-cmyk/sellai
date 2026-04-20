#!/usr/bin/env python3
"""
将短视频引流面板JavaScript添加到办公室HTML文件
"""

import os
import re

def append_short_video_js():
    html_file = "outputs/仪表盘/SellAI_办公室_短视频引流版.html"
    js_file = "src/short_video_panel.js"
    
    # 读取HTML文件
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # 读取短视频引流面板JS代码
    with open(js_file, 'r', encoding='utf-8') as f:
        js_code = f.read()
    
    # 找到最后一个</script>标签的位置
    last_script_pos = html_content.rfind('</script>')
    
    if last_script_pos == -1:
        print("错误: 未找到</script>标签")
        return False
    
    # 在最后一个</script>标签之前插入短视频引流面板JS
    # 我们需要先添加一个换行符
    insert_pos = last_script_pos
    
    # 查找前面的<script>标签的开始位置
    script_start = html_content.rfind('<script>', 0, insert_pos)
    if script_start == -1:
        # 尝试查找<script type="text/javascript">
        script_start = html_content.rfind('<script type="text/javascript">', 0, insert_pos)
    
    # 如果找到了脚本块的开始，我们在</script>前插入新代码
    if script_start != -1:
        # 在最后一个</script>标签前插入我们的JS代码
        new_html = html_content[:insert_pos] + '\n\n' + js_code + '\n\n' + html_content[insert_pos:]
        
        # 写入更新后的HTML文件
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(new_html)
        
        print(f"短视频引流面板JavaScript已添加到: {html_file}")
        return True
    
    # 如果没找到现有的脚本块，在</body>之前添加新的脚本块
    body_end_pos = html_content.rfind('</body>')
    if body_end_pos == -1:
        print("错误: 未找到</body>标签")
        return False
    
    # 在</body>之前添加新的<script>标签
    new_script = f'\n<script>\n{js_code}\n</script>\n'
    new_html = html_content[:body_end_pos] + new_script + html_content[body_end_pos:]
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(new_html)
    
    print(f"短视频引流面板JavaScript已添加到: {html_file}")
    return True

if __name__ == "__main__":
    success = append_short_video_js()
    exit(0 if success else 1)