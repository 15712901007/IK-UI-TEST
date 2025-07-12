#!/usr/bin/env python3
"""
单独执行VLAN搜索功能测试脚本
适用于已完成前置步骤（登录、添加VLAN等），只需要测试搜索功能的场景
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

class SearchOnlyTest:
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
            
            # 执行登录（LoginPage.login只接受username和password两个参数）
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
    
    def run_search_tests(self):
        """运行搜索功能测试"""
        try:
            self.logger.info("🔍 开始执行VLAN搜索功能测试...")
            
            vlan_page = VlanPage(self.page)
            
            # 加载搜索测试数据
            vlan_config = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            search_scenarios = vlan_config.get('search_test_data', {}).get('search_scenarios', [])
            
            self.logger.info(f"📋 共有 {len(search_scenarios)} 个搜索测试场景")
            
            success_count = 0
            total_count = len(search_scenarios)
            
            for i, scenario in enumerate(search_scenarios, 1):
                search_term = scenario.get('search_term', '')
                expected_vlans = scenario.get('expected_vlans', [])
                description = scenario.get('description', '')
                
                print(f"\n{'='*60}")
                print(f"🔍 搜索测试场景 {i}/{total_count}")
                print(f"📝 描述: {description}")
                print(f"🔑 搜索关键词: '{search_term}'")
                print(f"🎯 期望结果: {expected_vlans}")
                print(f"{'='*60}")
                
                self.logger.info(f"执行搜索测试场景 {i}: {description}")
                
                # 执行搜索
                search_result = vlan_page.search_vlan(search_term)
                
                if search_result:
                    self.logger.info("✅ 搜索操作执行成功")
                    
                    # 验证搜索结果
                    if scenario.get('expected_count') == "all":
                        # 空搜索应该显示所有结果
                        filtered_vlans = vlan_page.get_filtered_vlan_list()
                        if len(filtered_vlans) > 0:
                            self.logger.info(f"✅ 空搜索显示所有结果: {len(filtered_vlans)}条")
                            print(f"✅ 测试通过: 显示了 {len(filtered_vlans)} 条VLAN记录")
                            success_count += 1
                        else:
                            self.logger.error("❌ 空搜索应该显示所有结果，但结果为空")
                            print("❌ 测试失败: 空搜索应该显示所有结果")
                    else:
                        # 验证特定搜索结果
                        verify_result = vlan_page.verify_search_results(search_term, expected_vlans)
                        if verify_result:
                            self.logger.info("✅ 搜索结果验证通过")
                            print(f"✅ 测试通过: 找到期望的VLAN {expected_vlans}")
                            success_count += 1
                        else:
                            self.logger.error("❌ 搜索结果验证失败")
                            print("❌ 测试失败: 搜索结果不符合预期")
                else:
                    self.logger.error("❌ 搜索操作执行失败")
                    print("❌ 测试失败: 搜索操作执行失败")
                
                # 清空搜索框，准备下一次测试
                if i < total_count:  # 不是最后一个场景
                    self.logger.info("清空搜索框，准备下一次测试...")
                    vlan_page.clear_search()
                    time.sleep(1)
            
            # 输出测试结果
            print(f"\n{'='*60}")
            print(f"🎯 VLAN搜索功能测试结果")
            print(f"{'='*60}")
            print(f"📊 总测试场景: {total_count}")
            print(f"✅ 成功场景: {success_count}")
            print(f"❌ 失败场景: {total_count - success_count}")
            print(f"📈 成功率: {(success_count/total_count)*100:.1f}%")
            print(f"{'='*60}")
            
            if success_count == total_count:
                print("🎉 所有搜索功能测试通过！")
                self.logger.info("🎉 所有搜索功能测试通过！")
                return True
            else:
                print(f"⚠️  有 {total_count - success_count} 个测试场景失败")
                self.logger.warning(f"⚠️  有 {total_count - success_count} 个测试场景失败")
                return False
                
        except Exception as e:
            self.logger.error(f"搜索功能测试失败: {e}")
            print(f"❌ 搜索功能测试失败: {e}")
            return False
    
    def run(self):
        """运行测试"""
        try:
            print("🔍 VLAN搜索功能独立测试")
            print("=" * 60)
            print("📋 测试说明:")
            print("   - 仅执行搜索功能测试")
            print("   - 需要系统已登录且有VLAN数据")
            print("   - 测试6个搜索场景")
            print("=" * 60)
            
            # 设置浏览器
            if not self.setup_browser():
                return False
            
            # 快速登录
            if not self.quick_login():
                return False
            
            # 运行搜索测试
            result = self.run_search_tests()
            
            return result
            
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            print(f"❌ 测试执行失败: {e}")
            return False
        finally:
            self.cleanup_browser()

def main():
    """主函数"""
    test = SearchOnlyTest()
    success = test.run()
    
    if success:
        print("\n🎉 VLAN搜索功能测试成功完成！")
        sys.exit(0)
    else:
        print("\n❌ VLAN搜索功能测试失败！")
        sys.exit(1)

if __name__ == "__main__":
    main() 