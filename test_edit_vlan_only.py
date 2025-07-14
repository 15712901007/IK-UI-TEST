#!/usr/bin/env python3
"""
单独执行VLAN编辑功能测试脚本
适用于已完成前置步骤（登录、添加VLAN等），只需要测试编辑功能的场景
"""

import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from utils.logger import Logger
from utils.yaml_reader import YamlReader
from pages.vlan_page import VlanPage
from pages.login_page import LoginPage

class EditVlanOnlyTest:
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.page = None
        self.browser = None
        self.context = None
        
    def setup_browser(self):
        """设置浏览器"""
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=False,  # 显示浏览器，方便观察
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            self.page = self.context.new_page()
            self.logger.info("浏览器设置完成")
            return True
        except Exception as e:
            self.logger.error(f"设置浏览器失败: {e}")
            return False
    
    def cleanup_browser(self):
        """清理浏览器资源"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
            self.logger.info("浏览器资源清理完成")
        except Exception as e:
            self.logger.warning(f"清理浏览器资源失败: {e}")
    
    def quick_login(self):
        """快速登录到系统"""
        try:
            # 加载登录配置
            login_config = self.yaml_reader.read_yaml("data/login_data.yaml")
            if not login_config:
                self.logger.error("无法加载登录配置")
                return False
                
            login_data = login_config.get('login_data', {})
            
            # 创建登录页面对象
            login_page = LoginPage(self.page)
            
            # 执行登录
            self.logger.info("快速登录中...")
            if login_page.login(
                login_data.get('username', 'admin'),
                login_data.get('password', 'admin123')
            ):
                self.logger.info("✅ 登录成功")
                return True
            else:
                self.logger.error("❌ 登录失败")
                return False
                
        except Exception as e:
            self.logger.error(f"登录过程失败: {e}")
            return False
    
    def run_edit_test(self):
        """运行VLAN编辑功能测试"""
        try:
            self.logger.info("🔧 开始执行VLAN编辑功能测试...")
            
            vlan_page = VlanPage(self.page)
            
            # 加载编辑测试数据
            vlan_config = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            edit_test_data = vlan_config.get('edit_test_data', {})
            
            if not edit_test_data:
                self.logger.error("未找到编辑测试数据配置")
                return False
            
            target_vlan = edit_test_data.get('target_vlan', {})
            original_data = edit_test_data.get('original_data', {})
            edited_data = edit_test_data.get('edited_data', {})
            
            vlan_id = target_vlan.get('id', '888')
            
            print(f"\n{'='*70}")
            print(f"🔧 VLAN编辑功能测试")
            print(f"{'='*70}")
            print(f"📋 测试目标: VLAN{vlan_id} ({target_vlan.get('name', 'vlan888')})")
            print(f"📝 测试描述: {target_vlan.get('description', '编辑VLAN功能测试')}")
            print(f"{'='*70}")
            
            # 显示编辑前后的数据对比
            print(f"\n📊 数据变更计划:")
            print(f"┌─────────────┬─────────────────────┬─────────────────────┐")
            print(f"│    字段     │      编辑前         │      编辑后         │")
            print(f"├─────────────┼─────────────────────┼─────────────────────┤")
            print(f"│ VLAN名称    │ {original_data.get('vlan_name', ''):<19} │ {edited_data.get('vlan_name', ''):<19} │")
            print(f"│ IP地址      │ {original_data.get('ip_addr', ''):<19} │ {edited_data.get('ip_addr', ''):<19} │")
            print(f"│ 子网掩码    │ {original_data.get('subnet_mask', ''):<19} │ {edited_data.get('subnet_mask', ''):<19} │")
            print(f"│ 线路        │ {original_data.get('line', ''):<19} │ {edited_data.get('line_final', ''):<19} │")
            print(f"│ 备注        │ {original_data.get('comment', ''):<19} │ {edited_data.get('comment', ''):<19} │")
            if edited_data.get('extend_ips'):
                extend_ip = edited_data['extend_ips'][0]
                orig_extend = original_data.get('extend_ips', [{}])[0] if original_data.get('extend_ips') else {}
                print(f"│ 扩展IP      │ {orig_extend.get('ip', ''):<19} │ {extend_ip.get('ip', ''):<19} │")
                print(f"│ 扩展IP掩码  │ {orig_extend.get('mask', ''):<19} │ {extend_ip.get('mask', ''):<19} │")
            print(f"└─────────────┴─────────────────────┴─────────────────────┘")
            
            # 准备编辑数据（添加临时线路选择）
            edit_data_with_temp = edited_data.copy()
            if 'line' in edited_data and 'line_final' in edited_data:
                edit_data_with_temp['line_temp'] = edited_data.get('line', 'vlan201')
                edit_data_with_temp['line'] = edited_data.get('line_final', 'lan1')
            
            print(f"\n🚀 开始执行编辑操作...")
            
            # 执行编辑操作
            edit_result = vlan_page.edit_vlan(vlan_id, edit_data_with_temp)
            
            if edit_result:
                print(f"✅ VLAN编辑操作执行成功")
                
                # 验证编辑结果
                print(f"\n🔍 验证编辑结果...")
                verification_data = edit_test_data.get('verification_data', {})
                verify_result = vlan_page.verify_vlan_edited(vlan_id, verification_data)
                
                if verify_result:
                    print(f"✅ VLAN编辑结果验证通过")
                    
                    # 输出最终结果
                    print(f"\n{'='*70}")
                    print(f"🎉 VLAN编辑功能测试完成")
                    print(f"{'='*70}")
                    print(f"📊 测试结果: 成功")
                    print(f"🔧 编辑操作: 完成")
                    print(f"✅ 数据验证: 通过")
                    print(f"📝 API记录: 已保存到 api_logs/vlan/")
                    print(f"{'='*70}")
                    
                    return True
                else:
                    print(f"❌ VLAN编辑结果验证失败")
                    return False
            else:
                print(f"❌ VLAN编辑操作执行失败")
                return False
                
        except Exception as e:
            self.logger.error(f"VLAN编辑功能测试失败: {e}")
            print(f"❌ VLAN编辑功能测试失败: {e}")
            return False
    
    def run(self):
        """运行测试"""
        try:
            print("🔧 VLAN编辑功能独立测试")
            print("=" * 70)
            print("📋 测试说明:")
            print("   - 仅执行VLAN编辑功能测试")
            print("   - 需要系统已登录且有VLAN888数据")
            print("   - 测试完整的编辑流程")
            print("   - 包含取消按钮测试")
            print("   - 验证编辑结果")
            print("=" * 70)
            
            # 设置浏览器
            if not self.setup_browser():
                return False
            
            # 快速登录
            if not self.quick_login():
                return False
            
            # 运行编辑测试
            result = self.run_edit_test()
            
            return result
            
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            print(f"❌ 测试执行失败: {e}")
            return False
        finally:
            self.cleanup_browser()

def main():
    """主函数"""
    test = EditVlanOnlyTest()
    success = test.run()
    
    if success:
        print("\n🎉 VLAN编辑功能测试成功完成！")
        sys.exit(0)
    else:
        print("\n❌ VLAN编辑功能测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 