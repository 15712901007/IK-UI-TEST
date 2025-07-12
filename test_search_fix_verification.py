#!/usr/bin/env python3
"""
VLAN搜索功能修复验证脚本
根据用户录制的代码修复搜索功能后的验证测试
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

class SearchFixVerification:
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
    
    def login_to_system(self):
        """登录到系统"""
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
            self.logger.info("开始登录...")
            if login_page.login(
                login_data.get('username', 'admin'),
                login_data.get('password', 'admin123'),
                login_data.get('url', 'http://10.66.0.40')
            ):
                self.logger.info("✅ 登录成功")
                return True
            else:
                self.logger.error("❌ 登录失败")
                return False
                
        except Exception as e:
            self.logger.error(f"登录过程失败: {e}")
            return False
    
    def prepare_test_data(self):
        """准备测试数据"""
        try:
            self.logger.info("准备VLAN搜索测试数据...")
            
            vlan_page = VlanPage(self.page)
            
            # 加载测试数据
            vlan_config = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            if not vlan_config:
                self.logger.error("无法加载VLAN配置")
                return False
            
            # 确保有基础VLAN数据用于搜索测试
            basic_vlans = vlan_config.get('basic_vlans', [])
            batch_vlans = vlan_config.get('batch_vlans', [])
            
            # 检查是否已有测试数据
            current_vlans = vlan_page.get_vlan_list()
            existing_ids = [vlan['id'] for vlan in current_vlans]
            
            # 添加基础VLAN（如果不存在）
            for vlan in basic_vlans:
                if vlan['id'] not in existing_ids:
                    self.logger.info(f"添加基础VLAN: {vlan['id']}")
                    vlan_page.add_vlan(
                        vlan['id'], 
                        vlan['name'], 
                        vlan['ip_addr'], 
                        vlan['comment']
                    )
                    time.sleep(1)
            
            # 添加批量VLAN（如果不存在）
            for vlan in batch_vlans:
                if vlan['id'] not in existing_ids:
                    self.logger.info(f"添加批量VLAN: {vlan['id']}")
                    vlan_page.add_vlan(
                        vlan['id'], 
                        vlan['name'], 
                        vlan['ip_addr'], 
                        vlan['comment']
                    )
                    time.sleep(1)
            
            self.logger.info("✅ 测试数据准备完成")
            return True
            
        except Exception as e:
            self.logger.error(f"准备测试数据失败: {e}")
            return False
    
    def test_search_functionality(self):
        """测试搜索功能"""
        try:
            self.logger.info("开始验证VLAN搜索功能修复...")
            
            vlan_page = VlanPage(self.page)
            
            # 加载搜索测试数据
            vlan_config = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            search_scenarios = vlan_config.get('search_test_data', {}).get('search_scenarios', [])
            
            success_count = 0
            total_count = len(search_scenarios)
            
            for i, scenario in enumerate(search_scenarios, 1):
                search_term = scenario.get('search_term', '')
                expected_vlans = scenario.get('expected_vlans', [])
                description = scenario.get('description', '')
                
                self.logger.info(f"\n=== 搜索测试场景 {i}/{total_count}: {description} ===")
                self.logger.info(f"搜索关键词: '{search_term}'")
                self.logger.info(f"期望结果: {expected_vlans}")
                
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
                            success_count += 1
                        else:
                            self.logger.error("❌ 空搜索应该显示所有结果，但结果为空")
                    else:
                        # 验证特定搜索结果
                        verify_result = vlan_page.verify_search_results(search_term, expected_vlans)
                        if verify_result:
                            self.logger.info("✅ 搜索结果验证通过")
                            success_count += 1
                        else:
                            self.logger.error("❌ 搜索结果验证失败")
                else:
                    self.logger.error("❌ 搜索操作执行失败")
                
                # 清空搜索框，准备下一次测试
                if i < total_count:  # 不是最后一个场景
                    self.logger.info("清空搜索框，准备下一次测试...")
                    vlan_page.clear_search()
                    time.sleep(1)
            
            # 输出测试结果
            self.logger.info(f"\n=== 搜索功能验证结果 ===")
            self.logger.info(f"总测试场景: {total_count}")
            self.logger.info(f"成功场景: {success_count}")
            self.logger.info(f"失败场景: {total_count - success_count}")
            self.logger.info(f"成功率: {(success_count/total_count)*100:.1f}%")
            
            if success_count == total_count:
                self.logger.info("🎉 所有搜索功能测试通过！")
                return True
            else:
                self.logger.warning(f"⚠️  有 {total_count - success_count} 个测试场景失败")
                return False
                
        except Exception as e:
            self.logger.error(f"测试搜索功能失败: {e}")
            return False
    
    def run_verification(self):
        """运行验证测试"""
        try:
            self.logger.info("🚀 开始VLAN搜索功能修复验证...")
            
            # 设置浏览器
            if not self.setup_browser():
                return False
            
            # 登录系统
            if not self.login_to_system():
                return False
            
            # 准备测试数据
            if not self.prepare_test_data():
                return False
            
            # 测试搜索功能
            result = self.test_search_functionality()
            
            if result:
                self.logger.info("✅ VLAN搜索功能修复验证成功！")
                self.logger.info("🔧 修复要点:")
                self.logger.info("   1. 严格按照录制代码执行三步操作")
                self.logger.info("   2. 点击搜索框 → 输入内容 → 点击搜索按钮")
                self.logger.info("   3. 使用更精确的搜索数据避免模糊匹配")
                self.logger.info("   4. 增加详细的日志记录便于调试")
            else:
                self.logger.error("❌ VLAN搜索功能修复验证失败")
            
            return result
            
        except Exception as e:
            self.logger.error(f"验证测试失败: {e}")
            return False
        finally:
            self.cleanup_browser()

def main():
    """主函数"""
    print("=" * 80)
    print("🔍 VLAN搜索功能修复验证脚本")
    print("=" * 80)
    print("📋 验证内容:")
    print("   1. 严格按照用户录制代码执行搜索操作")
    print("   2. 验证三步操作：点击搜索框 → 输入内容 → 点击搜索按钮")
    print("   3. 测试更精确的搜索数据")
    print("   4. 确保搜索结果准确性")
    print("=" * 80)
    
    verification = SearchFixVerification()
    success = verification.run_verification()
    
    if success:
        print("\n🎉 验证成功！搜索功能已修复")
        sys.exit(0)
    else:
        print("\n❌ 验证失败！需要进一步检查")
        sys.exit(1)

if __name__ == "__main__":
    main() 