#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理重复的API文件脚本
"""

import sys
import os
from pathlib import Path

def cleanup_duplicate_api_files():
    """清理重复的API文件，只保留VLAN36的文件"""
    print("🧹 开始清理重复的API文件")
    print("=" * 50)
    
    api_dir = Path("api_logs/vlan")
    if not api_dir.exists():
        print("📁 API日志目录不存在，无需清理")
        return True
    
    # 查找所有API文件
    all_files = list(api_dir.glob("*.json")) + list(api_dir.glob("*.curl"))
    
    # 需要保留的文件（只保留VLAN36的）
    keep_patterns = [
        "add_vlan_36.",
        "show_vlan_after_add_36.",
    ]
    
    # 需要删除的文件
    files_to_delete = []
    files_to_keep = []
    
    for file in all_files:
        should_keep = False
        for pattern in keep_patterns:
            if pattern in file.name:
                should_keep = True
                break
        
        if should_keep:
            files_to_keep.append(file)
        else:
            # 检查是否是重复的add或show文件
            if (file.name.startswith("add_vlan_") and not file.name.startswith("add_vlan_36")) or \
               (file.name.startswith("show_vlan_after_add_") and not file.name.startswith("show_vlan_after_add_36")):
                files_to_delete.append(file)
    
    print(f"📊 文件统计:")
    print(f"  • 总文件数: {len(all_files)}")
    print(f"  • 保留文件: {len(files_to_keep)}")
    print(f"  • 删除文件: {len(files_to_delete)}")
    
    if files_to_keep:
        print(f"\n✅ 保留的文件:")
        for file in sorted(files_to_keep):
            print(f"  • {file.name}")
    
    if files_to_delete:
        print(f"\n🗑️ 准备删除的文件:")
        for file in sorted(files_to_delete):
            print(f"  • {file.name}")
        
        # 确认删除
        print(f"\n⚠️ 即将删除 {len(files_to_delete)} 个重复文件")
        confirm = input("确认删除吗？(y/N): ").strip().lower()
        
        if confirm == 'y':
            deleted_count = 0
            for file in files_to_delete:
                try:
                    file.unlink()
                    deleted_count += 1
                    print(f"🗑️ 已删除: {file.name}")
                except Exception as e:
                    print(f"❌ 删除失败: {file.name} - {e}")
            
            print(f"\n✅ 清理完成，已删除 {deleted_count}/{len(files_to_delete)} 个文件")
        else:
            print("❌ 取消删除操作")
    else:
        print(f"\n✅ 没有发现重复文件，无需清理")
    
    return True

def main():
    """主函数"""
    print("🚀 API文件清理工具")
    print("=" * 60)
    
    try:
        cleanup_duplicate_api_files()
        print("\n🎉 清理操作完成！")
        print("\n📋 清理后只保留:")
        print("  • add_vlan_36.json/curl - 添加VLAN的API示例")
        print("  • show_vlan_after_add_36.json/curl - 显示VLAN的API示例")
        
    except Exception as e:
        print(f"❌ 清理过程中出现错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 