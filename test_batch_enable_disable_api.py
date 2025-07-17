#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的全部启用/停用VLAN API抓取功能
"""

import time
from playwright.sync_api import sync_playwright
from pages.login_page import LoginPage
from pages.vlan_page import VlanPage
from utils.logger import Logger
from utils.yaml_reader import YamlReader

class BatchEnableDisableAPITest:
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.login_data = self.yaml_reader.read_yaml("data/login_data.yaml")
        
    def test_batch_api_capture(self):
        """测试批量启用/停用API抓取"""
        try:
            self.logger.info("🚀 开始测试批量启用/停用API抓取功能")
            
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                
                # 登录
                login_page = LoginPage(page)
                valid_login = self.login_data.get('valid_login', [{}])[0]
                if not login_page.login(
                    valid_login.get('username', 'admin'), 
                    valid_login.get('password', 'admin123')
                ):
                    self.logger.error("登录失败")
                    return False
                
                self.logger.info("✅ 登录成功")
                
                # 创建VLAN页面实例
                vlan_page = VlanPage(page)
                
                # 测试1: 全部停用VLAN
                self.logger.info("📋 测试1: 全部停用VLAN")
                if vlan_page.disable_all_vlans():
                    self.logger.info("✅ 全部停用VLAN测试成功")
                else:
                    self.logger.error("❌ 全部停用VLAN测试失败")
                
                # 等待一段时间
                time.sleep(3)
                
                # 测试2: 全部启用VLAN
                self.logger.info("📋 测试2: 全部启用VLAN")
                if vlan_page.enable_all_vlans():
                    self.logger.info("✅ 全部启用VLAN测试成功")
                else:
                    self.logger.error("❌ 全部启用VLAN测试失败")
                
                # 等待一段时间
                time.sleep(3)
                
                # 测试3: 再次全部停用VLAN
                self.logger.info("📋 测试3: 再次全部停用VLAN")
                if vlan_page.disable_all_vlans():
                    self.logger.info("✅ 再次全部停用VLAN测试成功")
                else:
                    self.logger.error("❌ 再次全部停用VLAN测试失败")
                
                self.logger.info("🎉 所有测试完成")
                
                # 保持浏览器打开以便观察
                input("按Enter键关闭浏览器...")
                browser.close()
                return True
                
        except Exception as e:
            self.logger.error(f"测试失败: {e}")
            return False

if __name__ == "__main__":
    test = BatchEnableDisableAPITest()
    success = test.test_batch_api_capture()
    if success:
        print("✅ 测试成功完成")
    else:
        print("❌ 测试失败") 