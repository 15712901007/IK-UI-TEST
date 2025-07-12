# 检查测试文件脚本
import os
import sys
from pathlib import Path

def check_test_files():
    """检查测试文件是否存在并且格式正确"""
    
    project_root = Path(__file__).parent
    
    print("🔍 检查测试文件...")
    print("=" * 50)
    
    # 需要检查的文件
    required_files = {
        "pages/__init__.py": "",
        "pages/base_page.py": "BasePage",
        "pages/login_page.py": "LoginPage", 
        "pages/vlan_page.py": "VlanPage",
        "tests/__init__.py": "",
        "tests/conftest.py": "@pytest.fixture",
        "tests/test_login.py": "TestLogin",
        "tests/test_vlan.py": "TestVlan",
        "utils/__init__.py": "",
        "utils/logger.py": "Logger",
        "utils/yaml_reader.py": "YamlReader",
        "utils/screenshot_helper.py": "ScreenshotHelper"
    }
    
    missing_files = []
    invalid_files = []
    
    for file_path, required_content in required_files.items():
        full_path = project_root / file_path
        
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"❌ 缺失: {file_path}")
        else:
            if required_content:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if required_content not in content:
                            invalid_files.append(file_path)
                            print(f"⚠️  内容错误: {file_path} (缺少: {required_content})")
                        else:
                            print(f"✅ 正确: {file_path}")
                except Exception as e:
                    invalid_files.append(file_path)
                    print(f"❌ 读取错误: {file_path} - {e}")
            else:
                print(f"✅ 存在: {file_path}")
    
    print("=" * 50)
    
    if missing_files or invalid_files:
        print(f"❌ 发现问题:")
        if missing_files:
            print(f"   缺失文件: {len(missing_files)} 个")
        if invalid_files:
            print(f"   内容错误: {len(invalid_files)} 个")
        
        print("\n🔧 解决方案:")
        print("1. 使用提供的完整代码重新创建文件")
        print("2. 确保所有类名和函数名正确")
        print("3. 检查文件编码为UTF-8")
        
        return False
    else:
        print("✅ 所有测试文件检查通过！")
        
        # 尝试导入测试
        try:
            sys.path.insert(0, str(project_root))
            from pages.login_page import LoginPage
            from pages.vlan_page import VlanPage
            print("✅ 导入测试通过！")
            return True
        except ImportError as e:
            print(f"❌ 导入测试失败: {e}")
            return False

if __name__ == "__main__":
    success = check_test_files()
    
    if success:
        print("\n🚀 测试文件准备就绪，可以运行测试了！")
        print("💡 运行命令: python main.py")
    else:
        print("\n❌ 请先修复测试文件问题")
    
    input("\n按回车键继续...")