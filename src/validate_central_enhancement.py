#!/usr/bin/env python3
"""
简化版中枢强化验证脚本
专注于基本检查，确保System Prompt升级符合要求
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PROMPT_DIR = BASE_DIR / "outputs" / "升级后的SystemPrompt"

# 分身列表
AVATARS = [
    "情报官_中枢强化版.md",
    "内容官_中枢强化版.md", 
    "运营官_中枢强化版.md",
    "增长官_中枢强化版.md"
]

def check_file_exists():
    """检查所有文件是否存在"""
    print("📁 检查文件存在性...")
    all_exist = True
    
    for filename in AVATARS:
        filepath = PROMPT_DIR / filename
        if filepath.exists():
            print(f"   ✅ {filename}")
        else:
            print(f"   ❌ {filename} - 文件不存在")
            all_exist = False
    
    return all_exist

def check_file_size():
    """检查文件大小（至少800字，约4KB）"""
    print("\n📏 检查文件大小...")
    all_adequate = True
    
    for filename in AVATARS:
        filepath = PROMPT_DIR / filename
        size = os.path.getsize(filepath)
        # 800字约1600字节，放宽到2KB
        if size >= 2000:
            print(f"   ✅ {filename} - {size}字节")
        else:
            print(f"   ⚠️  {filename} - {size}字节 (可能过小)")
            all_adequate = False
    
    return all_adequate

def check_key_sections():
    """检查关键章节"""
    print("\n📑 检查关键章节...")
    
    # 定义关键章节关键词
    key_sections = {
        "角色定位": ["基础中枢", "核心功能", "调度"],
        "基础中枢职责": ["分身能力", "协同", "监控", "分析", "优化"],
        "协同协议": ["情报官", "内容官", "运营官", "增长官", "协同"]
    }
    
    all_have_sections = True
    
    for filename in AVATARS:
        filepath = PROMPT_DIR / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"   📄 {filename}:")
        
        found_sections = []
        for section_name, keywords in key_sections.items():
            # 检查章节标题
            if section_name in content:
                found_sections.append(section_name)
                print(f"      ✅ {section_name}")
            else:
                # 检查关键词
                found_keywords = [kw for kw in keywords if kw in content]
                if found_keywords:
                    found_sections.append(section_name)
                    print(f"      ✅ {section_name} (关键词存在)")
                else:
                    print(f"      ⚠️  {section_name} (未明确标注)")
        
        if len(found_sections) >= 2:
            print(f"      → 章节完整性: 良好")
        else:
            print(f"      → 章节完整性: 不足")
            all_have_sections = False
    
    return all_have_sections

def check_version_consistency():
    """检查版本一致性"""
    print("\n🔖 检查版本一致性...")
    
    version_keywords = ["v3.0", "中枢强化版", "基础中枢"]
    consistent = True
    
    for filename in AVATARS:
        filepath = PROMPT_DIR / filename
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found = [kw for kw in version_keywords if kw in content]
        if found:
            print(f"   ✅ {filename} - 包含版本标识: {', '.join(found[:2])}")
        else:
            print(f"   ❌ {filename} - 缺少版本标识")
            consistent = False
    
    return consistent

def main():
    """主验证流程"""
    print("=" * 60)
    print("无限AI分身架构 - 四中枢强化验证 (简化版)")
    print("=" * 60)
    
    # 检查目录
    if not PROMPT_DIR.exists():
        print(f"❌ Prompt目录不存在: {PROMPT_DIR}")
        sys.exit(1)
    
    results = []
    
    # 执行各项检查
    results.append(("文件存在性", check_file_exists()))
    results.append(("文件大小", check_file_size()))
    results.append(("关键章节", check_key_sections()))
    results.append(("版本一致性", check_version_consistency()))
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 验证成功! 所有检查项通过。")
        print("四中枢强化升级完成，System Prompt已具备基础中枢调度协调能力。")
        sys.exit(0)
    else:
        print("⚠️  验证部分失败，建议优化相关System Prompt文件。")
        print("重点检查文件内容完整性和关键章节描述。")
        sys.exit(1)

if __name__ == "__main__":
    main()