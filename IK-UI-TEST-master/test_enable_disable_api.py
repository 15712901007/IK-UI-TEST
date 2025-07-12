#!/usr/bin/env python3
"""
测试启用/停用VLAN操作的API捕获功能
"""

import sys
import os
from pathlib import Path
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from playwright.sync_api import sync_playwright
from utils.logger import Logger
from pages.login_page import LoginPage
from pages.vlan_page import VlanPage
from utils.yaml_reader import YamlReader

def test_enable_disable_api():
    """测试启用和停用VLAN的API捕获"""
    logger = Logger().get_logger()
    yaml_reader = YamlReader()
    
    # 读取登录配置
    try:
        login_config = yaml_reader.read_yaml("data/login_data.yaml")
        # 使用有效登录的第一个配置
        valid_login = login_config['valid_login'][0]
        router_ip = "10.66.0.40"  # 默认IP
        username = valid_login['username']
        password = "admin123"  # 使用正确的密码
    except Exception as e:
        logger.error(f"读取登录配置失败: {e}")
        return False
    
    logger.info("🚀 开始启用/停用VLAN的API捕获测试")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()
        
        try:
            # 登录
            login_page = LoginPage(page)
            if not login_page.login(username, password):
                logger.error("登录失败")
                return False
            
            logger.info("✅ 登录成功")
            
            # 进入VLAN页面
            vlan_page = VlanPage(page)
            if not vlan_page.navigate_to_vlan_page():
                logger.error("导航到VLAN页面失败")
                return False
            
            logger.info("✅ 成功进入VLAN页面")
            
            # 获取VLAN列表
            vlans = vlan_page.get_vlan_list()
            if not vlans:
                logger.error("没有找到VLAN，请先添加一个VLAN")
                return False
            
            # 取第一个VLAN进行测试
            test_vlan = vlans[0]
            vlan_id = test_vlan['id']
            logger.info(f"📋 准备测试VLAN {vlan_id}")
            
            # 先检查当前VLAN状态
            current_status = vlan_page.get_vlan_status(vlan_id)
            logger.info(f"📊 当前VLAN {vlan_id} 状态: {current_status}")
            
            if current_status and "已启用" in current_status:
                # 当前是启用状态，测试停用操作
                logger.info("🔄 当前是启用状态，开始测试停用操作...")
                success = vlan_page.disable_vlan(vlan_id)
                if success:
                    logger.info("✅ 停用操作完成")
                    time.sleep(3)  # 等待页面更新
                    
                    # 再测试启用操作
                    logger.info("🔄 开始测试启用操作...")
                    success = vlan_page.enable_vlan(vlan_id)
                    if success:
                        logger.info("✅ 启用操作完成")
                    else:
                        logger.warning("⚠️ 启用操作未成功")
                else:
                    logger.warning("⚠️ 停用操作未成功")
            else:
                # 当前是停用状态，测试启用操作
                logger.info("🔄 当前是停用状态，开始测试启用操作...")
                success = vlan_page.enable_vlan(vlan_id)
                if success:
                    logger.info("✅ 启用操作完成")
                    time.sleep(3)  # 等待页面更新
                    
                    # 再测试停用操作
                    logger.info("🔄 开始测试停用操作...")
                    success = vlan_page.disable_vlan(vlan_id)
                    if success:
                        logger.info("✅ 停用操作完成")
                    else:
                        logger.warning("⚠️ 停用操作未成功")
                else:
                    logger.warning("⚠️ 启用操作未成功")
            
            logger.info("🎉 启用/停用API捕获测试完成")
            return True
            
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            return False
        finally:
            input("按Enter键关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    success = test_enable_disable_api()
    if success:
        print("✅ 测试成功完成")
    else:
        print("❌ 测试失败") 