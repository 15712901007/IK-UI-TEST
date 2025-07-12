#!/usr/bin/env python3
"""
测试启用/停用VLAN操作的API捕获功能 - 增加长时间等待
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

def test_enable_disable_with_long_wait():
    """测试启用和停用VLAN的API捕获 - 使用长时间等待"""
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
    
    logger.info("🚀 开始启用/停用VLAN的API捕获测试（长时间等待版本）")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)  # 更慢的操作
        page = browser.new_page()
        
        # 全局API监听器
        captured_calls = []
        
        def global_request_handler(req):
            """全局请求处理器"""
            try:
                if req.method.lower() != "post" or "/action/call" not in req.url.lower():
                    return
                
                body = req.post_data or ""
                if "\"func_name\":\"vlan\"" in body:
                    # 解析action
                    import re
                    m = re.search(r'"action"\s*:\s*"([A-Za-z0-9_]+)"', body)
                    action_val = "unknown"
                    if m:
                        action_val = m.group(1).lower()
                    
                    call_info = {
                        "action": action_val,
                        "url": req.url,
                        "body": body,
                        "timestamp": time.time()
                    }
                    captured_calls.append(call_info)
                    
                    logger.info(f"🎯 [全局监听] 捕获到VLAN API: action={action_val}")
                    logger.info(f"🎯 [全局监听] 请求体: {body[:100]}...")
                    
                    try:
                        resp_data = req.response().json()
                        logger.info(f"🎯 [全局监听] 响应: {resp_data}")
                    except:
                        logger.info(f"🎯 [全局监听] 响应状态: {req.response().status}")
                        
            except Exception as e:
                logger.error(f"处理请求时出错: {e}")
        
        # 设置全局监听器
        page.on("requestfinished", global_request_handler)
        logger.info("✅ 已设置全局API监听器")
        
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
            
            # 清空之前的API记录
            captured_calls.clear()
            logger.info("🧹 清空API记录，开始新的测试")
            
            if current_status and "已启用" in current_status:
                # 当前是启用状态，测试停用操作
                logger.info("🔄 当前是启用状态，开始测试停用操作...")
                
                # 找到停用按钮并点击
                rows = page.query_selector_all("table tbody tr")
                for row in rows:
                    cells = row.query_selector_all("td")
                    if cells and cells[0].text_content() and cells[0].text_content().strip() == str(vlan_id):
                        btns = row.query_selector_all("a")
                        for btn in btns:
                            if btn.text_content() and btn.text_content().strip() == "停用":
                                logger.info(f"🎯 找到停用按钮，准备点击...")
                                
                                btn.click()
                                logger.info(f"✅ 已点击停用按钮")
                                
                                # 长时间等待，模拟用户手动操作
                                logger.info("⏳ 等待30秒以捕获API调用...")
                                for i in range(300):  # 等待30秒，每100ms检查一次
                                    if captured_calls:
                                        logger.info(f"🎉 在第{i+1}次检查时检测到API调用！")
                                        for call in captured_calls:
                                            logger.info(f"  - Action: {call['action']}")
                                        break
                                    time.sleep(0.1)
                                else:
                                    logger.warning("⚠️ 等待30秒后仍未检测到API调用")
                                
                                break
                        break
                        
                logger.info("⏳ 再等待10秒以确保所有延迟的API调用都被捕获...")
                time.sleep(10)
                
            # 显示最终结果
            logger.info(f"📊 最终捕获到 {len(captured_calls)} 个API调用")
            for i, call in enumerate(captured_calls, 1):
                logger.info(f"  {i}. Action: {call['action']}, URL: {call['url']}")
            
            return True
            
        except Exception as e:
            logger.error(f"测试过程中出错: {e}")
            return False
        finally:
            logger.info("🔚 测试完成，浏览器将保持打开状态以观察...")
            input("按Enter键关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    success = test_enable_disable_with_long_wait()
    if success:
        print("✅ 测试成功完成")
    else:
        print("❌ 测试失败") 