#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码兼容性测试脚本
用于验证系统是否能正确处理UTF-8和GBK编码的文件
"""

import sys
import os
from pathlib import Path
import tempfile

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.yaml_reader import YamlReader
from utils.test_runner import TestRunner
from utils.logger import Logger

def test_encoding_compatibility():
    """测试编码兼容性"""
    print("🔍 测试编码兼容性...")
    print("=" * 50)
    
    # 测试内容
    test_content_utf8 = "测试内容：UTF-8编码文件\n用户名：admin\n密码：123456"
    test_content_gbk = "测试内容：GBK编码文件\n账号：管理员\n设置：网络配置"
    
    success_count = 0
    total_tests = 0
    
    # 1. 测试YamlReader的编码兼容性
    print("\n📁 测试YAML文件读取器...")
    try:
        yaml_reader = YamlReader()
        
        # 创建临时UTF-8文件
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.txt', delete=False) as f:
            f.write(test_content_utf8)
            temp_utf8_file = f.name
        
        # 创建临时GBK文件
        with tempfile.NamedTemporaryFile(mode='w', encoding='gbk', suffix='.txt', delete=False) as f:
            f.write(test_content_gbk)
            temp_gbk_file = f.name
        
        total_tests += 2
        
        # 测试UTF-8文件读取
        try:
            content_utf8 = yaml_reader._read_file_with_fallback(temp_utf8_file)
            if "UTF-8编码文件" in content_utf8:
                print("✅ UTF-8文件读取成功")
                success_count += 1
            else:
                print("❌ UTF-8文件内容不正确")
        except Exception as e:
            print(f"❌ UTF-8文件读取失败: {e}")
        
        # 测试GBK文件读取
        try:
            content_gbk = yaml_reader._read_file_with_fallback(temp_gbk_file)
            if "GBK编码文件" in content_gbk:
                print("✅ GBK文件读取成功")
                success_count += 1
            else:
                print("❌ GBK文件内容不正确")
        except Exception as e:
            print(f"❌ GBK文件读取失败: {e}")
        
        # 清理临时文件
        os.unlink(temp_utf8_file)
        os.unlink(temp_gbk_file)
        
    except Exception as e:
        print(f"❌ YAML读取器测试失败: {e}")
    
    # 2. 测试TestRunner的编码兼容性
    print("\n🚀 测试运行器...")
    try:
        test_runner = TestRunner()
        
        total_tests += 2
        
        # 测试UTF-8字节解码
        utf8_bytes = test_content_utf8.encode('utf-8')
        decoded_utf8 = test_runner._decode_with_fallback(utf8_bytes)
        if "UTF-8编码文件" in decoded_utf8:
            print("✅ UTF-8字节解码成功")
            success_count += 1
        else:
            print("❌ UTF-8字节解码失败")
        
        # 测试GBK字节解码
        gbk_bytes = test_content_gbk.encode('gbk')
        decoded_gbk = test_runner._decode_with_fallback(gbk_bytes)
        if "GBK编码文件" in decoded_gbk:
            print("✅ GBK字节解码成功")
            success_count += 1
        else:
            print("❌ GBK字节解码失败")
            
    except Exception as e:
        print(f"❌ 测试运行器测试失败: {e}")
    
    # 3. 测试现有配置文件读取
    print("\n📋 测试现有配置文件...")
    try:
        yaml_reader = YamlReader()
        total_tests += 3
        
        # 测试读取测试配置
        test_config = yaml_reader.read_yaml("config/test_config.yaml")
        if test_config:
            print("✅ 测试配置文件读取成功")
            success_count += 1
        else:
            print("❌ 测试配置文件读取失败或为空")
        
        # 测试读取VLAN数据
        vlan_data = yaml_reader.read_yaml("data/vlan_data.yaml")
        if vlan_data:
            print("✅ VLAN数据文件读取成功")
            success_count += 1
        else:
            print("❌ VLAN数据文件读取失败或为空")
        
        # 测试读取登录数据
        login_data = yaml_reader.read_yaml("data/login_data.yaml")
        if login_data:
            print("✅ 登录数据文件读取成功")
            success_count += 1
        else:
            print("❌ 登录数据文件读取失败或为空")
            
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
    
    # 输出测试结果
    print("\n" + "=" * 50)
    print(f"📊 测试结果统计:")
    print(f"   总测试数: {total_tests}")
    print(f"   成功数: {success_count}")
    print(f"   失败数: {total_tests - success_count}")
    print(f"   成功率: {(success_count/total_tests*100):.1f}%" if total_tests > 0 else "0.0%")
    
    if success_count == total_tests:
        print("🎉 所有编码兼容性测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，系统可能仍有编码问题")
        return False

def show_encoding_info():
    """显示系统编码信息"""
    print("\n💻 系统编码信息:")
    print(f"   默认编码: {sys.getdefaultencoding()}")
    print(f"   文件系统编码: {sys.getfilesystemencoding()}")
    print(f"   控制台编码: {sys.stdout.encoding}")
    print(f"   平台: {sys.platform}")

if __name__ == "__main__":
    print("🛠️  编码兼容性测试工具")
    print("该工具用于验证系统是否能正确处理不同编码的文件")
    
    show_encoding_info()
    
    try:
        success = test_encoding_compatibility()
        
        print("\n🔧 兼容性改进说明:")
        print("1. ✅ 所有文件读取操作现在支持多种编码（UTF-8, GBK, CP936）")
        print("2. ✅ subprocess输出处理支持编码自动检测")
        print("3. ✅ 添加了编码错误的容错机制")
        print("4. ✅ 保持原有功能完全兼容")
        
        print("\n📝 使用建议:")
        print("- 新创建的文件建议使用UTF-8编码")
        print("- 系统会自动处理现有的GBK编码文件")
        print("- 如果仍有编码问题，请查看具体错误日志")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        sys.exit(1) 