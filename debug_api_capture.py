#!/usr/bin/env python3
# 调试API捕获脚本

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from pages.login_page import LoginPage
from pages.vlan_page import VlanPage
from utils.logger import Logger
from utils.yaml_reader import YamlReader

class APIDebugTest:
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.browser = None
        self.page = None
        
    def setup_browser(self):
        """设置浏览器"""
        self.logger.info("设置浏览器...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=False,  # 显示浏览器
            slow_mo=500  # 减慢操作速度
        )
        self.page = self.browser.new_page()
        
    def cleanup_browser(self):
        """清理浏览器资源"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        self.logger.info("浏览器资源清理完成")
        
    def login(self):
        """登录"""
        self.logger.info("开始登录...")
        login_page = LoginPage(self.page)
        
        # 直接使用固定的登录信息
        if login_page.login("admin", "admin123"):
            self.logger.info("✅ 登录成功")
            return True
        else:
            self.logger.error("❌ 登录失败")
            return False
            
    def test_api_capture(self):
        """测试API捕获"""
        try:
            self.logger.info("开始测试API捕获...")
            
            vlan_page = VlanPage(self.page)
            
            # 导航到VLAN页面
            if not vlan_page.navigate_to_vlan_page():
                self.logger.error("导航到VLAN页面失败")
                return False
                
            # 等待页面加载
            import time
            time.sleep(2)
            
            # 设置一个通用的API监听器来捕获所有请求
            captured_requests = []
            
            def capture_all_requests(req):
                if req.method.lower() == "post":
                    captured_requests.append({
                        "url": req.url,
                        "method": req.method,
                        "post_data": req.post_data,
                        "headers": dict(req.headers)
                    })
                    self.logger.info(f"[通用监听] 捕获POST请求: {req.url}")
                    if req.post_data:
                        self.logger.info(f"[通用监听] 请求体: {req.post_data[:500]}...")
            
                         # 设置通用监听器
            self.page.on("request", capture_all_requests)
            
            # 同时监听response事件
            def capture_all_responses(resp):
                if resp.request.method.lower() == "post":
                    self.logger.info(f"[响应监听] 响应: {resp.status} {resp.url}")
                    
            self.page.on("response", capture_all_responses)
            
            # 点击编辑按钮
            self.logger.info("点击VLAN888编辑按钮...")
            if not vlan_page._click_vlan_edit_button("888"):
                self.logger.error("点击编辑按钮失败")
                return False
                
            time.sleep(2)
            
            # 简单修改一个字段
            self.logger.info("修改VLAN名称...")
            try:
                name_input = self.page.locator("input[name='vlan_name']")
                if name_input.count() > 0:
                    name_input.fill("test_debug")
                    self.logger.info("✅ 修改VLAN名称成功")
                else:
                    self.logger.warning("未找到VLAN名称输入框")
            except Exception as e:
                self.logger.warning(f"修改VLAN名称失败: {e}")
            
            # 清空之前的捕获记录
            captured_requests.clear()
            self.logger.info("清空之前的请求记录，开始监听保存操作...")
            
            # 点击保存按钮
            self.logger.info("点击保存按钮...")
            try:
                                 save_button = self.page.get_by_role("button", name="保存")
                if save_button.count() > 0:
                    # 记录点击前的URL
                    url_before = self.page.url
                    self.logger.info(f"点击前URL: {url_before}")
                    
                    save_button.click()
                    self.logger.info("✅ 已点击保存按钮")
                    
                    # 检查URL是否发生变化
                    time.sleep(1)
                    url_after = self.page.url
                    self.logger.info(f"点击后URL: {url_after}")
                    
                    if url_before != url_after:
                        self.logger.info("🔄 检测到页面跳转")
                    else:
                        self.logger.info("📍 页面未发生跳转")
                    
                    # 等待请求
                    self.logger.info("等待API请求...")
                    for i in range(100):  # 等待10秒
                        if captured_requests:
                            self.logger.info(f"🎉 在第{i+1}次检查时捕获到{len(captured_requests)}个请求")
                            break
                        time.sleep(0.1)
                    else:
                        self.logger.warning("⚠️ 等待10秒后仍未捕获到任何请求")
                        
                    # 显示捕获到的请求
                    for i, req in enumerate(captured_requests):
                        self.logger.info(f"请求{i+1}: {req['method']} {req['url']}")
                        if req['post_data']:
                            self.logger.info(f"请求体{i+1}: {req['post_data']}")
                            
                else:
                    self.logger.error("未找到保存按钮")
                    
            except Exception as e:
                self.logger.error(f"保存操作失败: {e}")
                
            # 清理监听器
            self.page.remove_listener("request", capture_all_requests)
            
            return True
            
        except Exception as e:
            self.logger.error(f"测试API捕获失败: {e}")
            return False
            
    def run(self):
        """运行测试"""
        try:
            self.setup_browser()
            
            if not self.login():
                return False
                
            if not self.test_api_capture():
                return False
                
            self.logger.info("🎉 API捕获测试完成")
            
        except Exception as e:
            self.logger.error(f"测试运行失败: {e}")
        finally:
            self.cleanup_browser()

def main():
    print("🔧 API捕获调试测试")
    print("=" * 60)
    
    test = APIDebugTest()
    test.run()

if __name__ == "__main__":
    main() 