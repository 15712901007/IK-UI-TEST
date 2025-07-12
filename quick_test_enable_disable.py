#!/usr/bin/env python3
"""
快速测试启用/停用VLAN的API监听
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import time
from pages.vlan_page import VlanPage
from pages.login_page import LoginPage
from utils.logger import Logger
from playwright.sync_api import sync_playwright

def test_enable_disable_single_vlan():
    """快速测试单个VLAN的启用/停用API监听"""
    logger = Logger().get_logger()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 可视化浏览器
        context = browser.new_context()
        page = context.new_page()
        
        try:
            logger.info("🚀 开始快速测试启用/停用API监听")
            
            # 登录
            login_page = LoginPage(page)
            if not login_page.login("admin", "admin123"):
                logger.error("❌ 登录失败")
                return False
            
            # 创建VLAN页面对象
            vlan_page = VlanPage(page)
            
            # 获取现有VLAN列表
            vlans = vlan_page.get_vlan_list()
            if not vlans:
                logger.error("❌ 未找到任何VLAN，请先添加VLAN")
                return False
            
            # 选择第一个VLAN进行测试
            test_vlan = vlans[0]
            vlan_id = test_vlan['id']
            
            logger.info(f"📋 选择VLAN {vlan_id} 进行测试")
            
            # 测试停用操作
            logger.info("🔄 测试停用操作...")
            result1 = vlan_page.disable_vlan(vlan_id)
            logger.info(f"停用结果: {'✅ 成功' if result1 else '❌ 失败'}")
            
            time.sleep(3)  # 等待状态更新
            
            # 测试启用操作
            logger.info("🔄 测试启用操作...")
            result2 = vlan_page.enable_vlan(vlan_id)
            logger.info(f"启用结果: {'✅ 成功' if result2 else '❌ 失败'}")
            
            # 总结
            if result1 and result2:
                logger.info("✅ 启用/停用测试完成")
                return True
            else:
                logger.error("❌ 启用/停用测试失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 测试过程中出错: {e}")
            return False
            
        finally:
            browser.close()

if __name__ == "__main__":
    test_enable_disable_single_vlan() 