#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLAN搜索功能测试脚本
独立测试VLAN搜索功能的完整性和准确性
"""

import sys
import os
from pathlib import Path
import time
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pages.vlan_page import VlanPage
from utils.yaml_reader import YamlReader
from utils.logger import Logger

class VlanSearchTester:
    """VLAN搜索功能测试器"""
    
    def __init__(self):
        self.yaml_reader = YamlReader()
        self.logger = Logger().get_logger()
        self.vlan_data = None
        
    def load_test_data(self):
        """加载测试数据"""
        try:
            self.vlan_data = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            if not self.vlan_data:
                raise Exception("VLAN测试数据为空")
            self.logger.info("✅ 测试数据加载成功")
            return True
        except Exception as e:
            self.logger.error(f"❌ 加载测试数据失败: {e}")
            return False
    
    def test_search_functionality(self, page):
        """测试搜索功能"""
        if not self.load_test_data():
            return False
            
        try:
            vlan_page = VlanPage(page)
            
            # 获取搜索测试场景
            search_test_data = self.vlan_data.get('search_test_data', {})
            search_scenarios = search_test_data.get('search_scenarios', [])
            
            self.logger.info(f"🔍 开始测试 {len(search_scenarios)} 个搜索场景")
            
            # 确保有足够的测试数据
            self.logger.info("📝 准备测试数据...")
            initial_vlans = vlan_page.get_vlan_list()
            self.logger.info(f"当前系统中有 {len(initial_vlans)} 个VLAN")
            
            # 如果VLAN数量不足，添加测试数据
            if len(initial_vlans) < 5:
                self.logger.info("添加测试数据...")
                basic_vlans = self.vlan_data.get('basic_vlans', [])
                batch_vlans = self.vlan_data.get('batch_vlans', [])
                
                # 添加基础VLAN
                for vlan in basic_vlans[:2]:
                    result = vlan_page.add_vlan(
                        vlan_id=vlan['id'],
                        vlan_name=vlan['name'],
                        ip_addr=vlan['ip_addr'],
                        comment=vlan.get('comment', '')
                    )
                    if result:
                        self.logger.info(f"✅ 已添加VLAN {vlan['id']}")
                
                # 添加批量VLAN
                for vlan in batch_vlans[:3]:
                    result = vlan_page.add_vlan(
                        vlan_id=vlan['id'],
                        vlan_name=vlan['name'],
                        ip_addr=vlan['ip_addr'],
                        comment=vlan.get('comment', '')
                    )
                    if result:
                        self.logger.info(f"✅ 已添加VLAN {vlan['id']}")
            
            # 重新获取VLAN列表
            all_vlans = vlan_page.get_vlan_list()
            self.logger.info(f"准备完成，当前系统中有 {len(all_vlans)} 个VLAN")
            
            # 执行搜索测试
            passed_count = 0
            failed_count = 0
            
            for i, scenario in enumerate(search_scenarios, 1):
                search_type = scenario.get('search_type', '')
                search_term = scenario.get('search_term', '')
                expected_count = scenario.get('expected_count', 0)
                expected_vlans = scenario.get('expected_vlans', [])
                description = scenario.get('description', '')
                
                self.logger.info(f"\n🧪 测试场景 {i}/{len(search_scenarios)}: {description}")
                self.logger.info(f"搜索内容: '{search_term}'")
                
                # 执行搜索
                if vlan_page.search_vlan(search_term):
                    # 验证搜索结果
                    if search_type == "empty_search":
                        # 空搜索应该显示所有结果
                        filtered_vlans = vlan_page.get_filtered_vlan_list()
                        if len(filtered_vlans) >= len(all_vlans) * 0.8:  # 允许一定误差
                            self.logger.info(f"✅ 空搜索显示所有结果，验证通过")
                            passed_count += 1
                        else:
                            self.logger.error(f"❌ 空搜索应显示所有结果，实际显示 {len(filtered_vlans)} 个")
                            failed_count += 1
                    elif expected_count == 0:
                        # 应该没有匹配结果
                        if vlan_page.verify_search_results(search_term, expected_vlans):
                            self.logger.info(f"✅ 无匹配结果验证通过")
                            passed_count += 1
                        else:
                            self.logger.error(f"❌ 无匹配结果验证失败")
                            failed_count += 1
                    else:
                        # 验证具体的搜索结果
                        if vlan_page.verify_search_results(search_term, expected_vlans):
                            self.logger.info(f"✅ 搜索结果验证通过")
                            passed_count += 1
                        else:
                            self.logger.error(f"❌ 搜索结果验证失败")
                            failed_count += 1
                else:
                    self.logger.error(f"❌ 搜索操作失败")
                    failed_count += 1
                
                # 清空搜索
                vlan_page.clear_search()
                time.sleep(1)
            
            # 测试实时过滤效果
            self.logger.info(f"\n🔄 测试实时过滤效果")
            test_term = "vlan"
            for i in range(1, len(test_term) + 1):
                partial_term = test_term[:i]
                vlan_page.search_vlan(partial_term)
                filtered_count = len(vlan_page.get_filtered_vlan_list())
                self.logger.info(f"输入'{partial_term}'，过滤后显示 {filtered_count} 个结果")
                time.sleep(0.5)
            
            # 清空搜索
            vlan_page.clear_search()
            
            # 总结结果
            self.logger.info(f"\n📊 搜索功能测试总结:")
            self.logger.info(f"测试场景总数: {len(search_scenarios)}")
            self.logger.info(f"通过场景数: {passed_count}")
            self.logger.info(f"失败场景数: {failed_count}")
            
            if failed_count == 0:
                self.logger.info("🎉 VLAN搜索功能测试全部通过!")
                return True
            else:
                self.logger.error(f"❌ VLAN搜索功能测试存在 {failed_count} 个失败场景")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 搜索功能测试异常: {e}")
            return False

def main():
    """主函数"""
    print("🚀 VLAN搜索功能测试开始")
    print("=" * 60)
    
    # 这里需要根据实际情况创建page对象
    # 由于这是一个独立的测试脚本，需要配合实际的测试环境使用
    
    tester = VlanSearchTester()
    
    # 加载测试数据
    if tester.load_test_data():
        print("✅ 测试数据加载成功")
        
        # 显示测试场景
        search_scenarios = tester.vlan_data.get('search_test_data', {}).get('search_scenarios', [])
        print(f"\n📋 将测试以下 {len(search_scenarios)} 个搜索场景:")
        for i, scenario in enumerate(search_scenarios, 1):
            print(f"{i}. {scenario.get('description', '')}")
            print(f"   搜索内容: '{scenario.get('search_term', '')}'")
        
        print("\n💡 提示: 此脚本需要配合实际的浏览器页面对象使用")
        print("请在实际的测试环境中调用 tester.test_search_functionality(page)")
    else:
        print("❌ 测试数据加载失败")
    
    print("=" * 60)

if __name__ == "__main__":
    main() 