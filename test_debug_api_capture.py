#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本的API捕获测试 - 使用双重监听器确保捕获所有VLAN API调用
"""

import time
from playwright.sync_api import sync_playwright
from pages.login_page import LoginPage
from pages.vlan_page import VlanPage
from utils.logger import Logger
from utils.yaml_reader import YamlReader

class DebugAPICapture:
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.login_data = self.yaml_reader.read_yaml("data/login_data.yaml")
        self.captured_requests = []
        self.captured_responses = []
        
    def setup_debug_listeners(self, page):
        """设置调试监听器"""
        
        def on_request(request):
            if request.method.lower() == "post" and "/action/call" in request.url.lower():
                body = request.post_data or ""
                if "vlan" in body.lower():
                    self.logger.info(f"🔍 [REQUEST] {request.method} {request.url}")
                    self.logger.info(f"🔍 [REQUEST-BODY] {body}")
                    self.captured_requests.append({
                        "timestamp": time.time(),
                        "method": request.method,
                        "url": request.url,
                        "body": body
                    })
        
        def on_response(response):
            if response.request.method.lower() == "post" and "/action/call" in response.url.lower():
                body = response.request.post_data or ""
                if "vlan" in body.lower():
                    self.logger.info(f"🔍 [RESPONSE] {response.status} {response.url}")
                    try:
                        resp_json = response.json()
                        self.logger.info(f"🔍 [RESPONSE-BODY] {resp_json}")
                        
                        # 解析action
                        import re
                        m = re.search(r'"action"\s*:\s*"([A-Za-z0-9_]+)"', body)
                        action = m.group(1) if m else "unknown"
                        
                        self.captured_responses.append({
                            "timestamp": time.time(),
                            "status": response.status,
                            "url": response.url,
                            "request_body": body,
                            "response_body": resp_json,
                            "action": action
                        })
                    except Exception as e:
                        self.logger.warning(f"解析响应失败: {e}")
        
        page.on("request", on_request)
        page.on("response", on_response)
        
    def test_debug_capture(self):
        """调试API捕获"""
        try:
            self.logger.info("🚀 开始调试API捕获测试")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                
                # 设置调试监听器
                self.setup_debug_listeners(page)
                
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
                
                # 导航到VLAN页面
                self.logger.info("📋 导航到VLAN页面")
                vlan_page.navigate_to_vlan_page()
                time.sleep(3)
                
                # 清空之前的捕获记录
                self.captured_requests.clear()
                self.captured_responses.clear()
                
                # 测试停用操作
                self.logger.info("📋 测试停用操作")
                
                # 点击全选
                checkbox = vlan_page._find_select_all_checkbox()
                if checkbox:
                    checkbox.click()
                    self.logger.info("✅ 已点击全选复选框")
                    time.sleep(2)
                    
                    # 点击停用按钮
                    self.logger.info("🎯 点击停用按钮...")
                    page.get_by_role("link", name="停用").click()
                    self.logger.info("✅ 已点击停用按钮")
                    
                    # 等待API调用
                    self.logger.info("⏳ 等待10秒捕获API调用...")
                    time.sleep(10)
                    
                    # 显示捕获结果
                    self.logger.info(f"📊 捕获到 {len(self.captured_requests)} 个请求")
                    self.logger.info(f"📊 捕获到 {len(self.captured_responses)} 个响应")
                    
                    for i, resp in enumerate(self.captured_responses):
                        self.logger.info(f"📋 响应{i+1}: action={resp['action']}, status={resp['status']}")
                        self.logger.info(f"    请求体: {resp['request_body'][:100]}...")
                        self.logger.info(f"    响应体: {resp['response_body']}")
                    
                    # 等待页面更新
                    time.sleep(3)
                    
                    # 再次清空记录
                    self.captured_requests.clear()
                    self.captured_responses.clear()
                    
                    # 测试启用操作
                    self.logger.info("📋 测试启用操作")
                    
                    # 点击全选
                    checkbox = vlan_page._find_select_all_checkbox()
                    if checkbox:
                        checkbox.click()
                        self.logger.info("✅ 已点击全选复选框")
                        time.sleep(2)
                        
                        # 点击启用按钮
                        self.logger.info("🎯 点击启用按钮...")
                        page.get_by_role("link", name="启用").click()
                        self.logger.info("✅ 已点击启用按钮")
                        
                        # 等待API调用
                        self.logger.info("⏳ 等待10秒捕获API调用...")
                        time.sleep(10)
                        
                        # 显示捕获结果
                        self.logger.info(f"📊 捕获到 {len(self.captured_requests)} 个请求")
                        self.logger.info(f"📊 捕获到 {len(self.captured_responses)} 个响应")
                        
                        for i, resp in enumerate(self.captured_responses):
                            self.logger.info(f"📋 响应{i+1}: action={resp['action']}, status={resp['status']}")
                            self.logger.info(f"    请求体: {resp['request_body'][:100]}...")
                            self.logger.info(f"    响应体: {resp['response_body']}")
                
                input("按Enter键关闭浏览器...")
                browser.close()
                
            self.logger.info("🎉 调试测试完成")
            return True
            
        except Exception as e:
            self.logger.error(f"调试测试失败: {e}")
            return False

if __name__ == "__main__":
    test = DebugAPICapture()
    success = test.test_debug_capture()
    if success:
        print("✅ 调试测试成功完成")
    else:
        print("❌ 调试测试失败") 