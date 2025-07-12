#!/usr/bin/env python3
"""
调试所有网络请求，找出启用/停用操作的真实接口
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

def debug_all_network_requests():
    """监听所有网络请求，找出启用/停用的真实接口"""
    logger = Logger().get_logger()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # 记录所有网络请求
        all_requests = []
        vlan_related_requests = []
        
        def handle_request_finished(request):
            """处理所有网络请求"""
            try:
                method = request.method
                url = request.url
                post_data = request.post_data or ""
                
                # 记录所有请求
                request_info = {
                    "method": method,
                    "url": url,
                    "post_data": post_data,
                    "timestamp": time.time()
                }
                all_requests.append(request_info)
                
                # 过滤可能与VLAN相关的请求
                if any(keyword in url.lower() for keyword in ['vlan', 'action', 'call', 'api']):
                    vlan_related_requests.append(request_info)
                    logger.info(f"🔍 [VLAN相关] {method} {url}")
                    if post_data:
                        logger.info(f"🔍 [VLAN相关] 请求体: {post_data}")
                        
                # 特别关注POST请求
                if method.upper() == "POST":
                    if "vlan" in post_data.lower() or "vlan" in url.lower():
                        logger.info(f"📡 [POST-VLAN] {url}")
                        logger.info(f"📡 [POST-VLAN] 数据: {post_data}")
                        try:
                            resp = request.response()
                            logger.info(f"📡 [POST-VLAN] 响应状态: {resp.status}")
                            if resp.status == 200:
                                try:
                                    resp_json = resp.json()
                                    logger.info(f"📡 [POST-VLAN] 响应内容: {resp_json}")
                                except:
                                    resp_text = resp.text()[:500]
                                    logger.info(f"📡 [POST-VLAN] 响应文本: {resp_text}")
                        except Exception as e:
                            logger.warning(f"无法获取响应: {e}")
                            
            except Exception as e:
                logger.error(f"处理请求时出错: {e}")
        
        def handle_request(request):
            """处理请求开始事件"""
            try:
                # 在请求发送前就记录
                if request.method.upper() == "POST" and any(keyword in request.url.lower() for keyword in ['vlan', 'action', 'call']):
                    logger.info(f"🚀 [即将发送] {request.method} {request.url}")
            except Exception as e:
                logger.error(f"处理即将发送的请求时出错: {e}")
        
        # 设置监听器
        page.on("request", handle_request)
        page.on("requestfinished", handle_request_finished)
        logger.info("✅ 已设置全面的网络监听器")
        
        try:
            logger.info("🚀 开始网络请求调试")
            
            # 登录
            login_page = LoginPage(page)
            if not login_page.login("admin", "admin123"):
                logger.error("❌ 登录失败")
                return False
            
            # 创建VLAN页面对象
            vlan_page = VlanPage(page)
            
            # 导航到VLAN页面
            logger.info("📍 导航到VLAN页面...")
            vlan_page.navigate_to_vlan_page()
            
            # 获取现有VLAN列表
            vlans = vlan_page.get_vlan_list()
            if not vlans:
                logger.error("❌ 未找到任何VLAN")
                return False
            
            test_vlan = vlans[0]
            vlan_id = test_vlan['id']
            logger.info(f"📋 准备测试VLAN {vlan_id}")
            
            # 清空之前的记录
            vlan_related_requests.clear()
            
            # 手动找到停用按钮并点击
            logger.info("🔄 开始停用操作，监听所有网络请求...")
            
            # 不使用封装的方法，直接操作页面元素
            try:
                # 找到VLAN行
                rows = page.query_selector_all("table tbody tr")
                target_row = None
                
                for row in rows:
                    cells = row.query_selector_all("td")
                    if cells and cells[0].text_content() and cells[0].text_content().strip() == str(vlan_id):
                        target_row = row
                        break
                
                if target_row:
                    # 找到停用按钮
                    buttons = target_row.query_selector_all("a")
                    disable_btn = None
                    
                    for btn in buttons:
                        btn_text = btn.text_content()
                        if btn_text and "停用" in btn_text:
                            disable_btn = btn
                            break
                    
                    if disable_btn:
                        logger.info("🎯 找到停用按钮，准备点击...")
                        logger.info("📊 点击前网络请求计数: " + str(len(all_requests)))
                        
                        # 点击停用按钮
                        disable_btn.click()
                        logger.info("✅ 已点击停用按钮")
                        
                        # 等待网络请求
                        time.sleep(5)
                        
                        logger.info("📊 点击后网络请求计数: " + str(len(all_requests)))
                        logger.info(f"📊 VLAN相关请求数量: {len(vlan_related_requests)}")
                        
                        # 显示最近的VLAN相关请求
                        if vlan_related_requests:
                            logger.info("📋 最近的VLAN相关请求:")
                            for i, req in enumerate(vlan_related_requests[-5:], 1):
                                logger.info(f"  {i}. {req['method']} {req['url']}")
                                if req['post_data']:
                                    logger.info(f"     数据: {req['post_data']}")
                        
                    else:
                        logger.error("❌ 未找到停用按钮")
                else:
                    logger.error(f"❌ 未找到VLAN {vlan_id} 的行")
                    
            except Exception as e:
                logger.error(f"❌ 手动操作时出错: {e}")
            
            # 等待一段时间确保捕获所有请求
            logger.info("⏳ 等待5秒以捕获所有可能的延迟请求...")
            time.sleep(5)
            
            # 总结结果
            logger.info("\n" + "="*50)
            logger.info("📊 网络请求分析总结")
            logger.info("="*50)
            logger.info(f"总请求数量: {len(all_requests)}")
            logger.info(f"VLAN相关请求数量: {len(vlan_related_requests)}")
            
            # 显示所有VLAN相关的请求
            if vlan_related_requests:
                logger.info("\n🔍 所有VLAN相关请求:")
                for i, req in enumerate(vlan_related_requests, 1):
                    logger.info(f"  {i}. {req['method']} {req['url']}")
                    if req['post_data']:
                        logger.info(f"     数据: {req['post_data'][:200]}...")
            else:
                logger.warning("⚠️ 未捕获到任何VLAN相关请求")
                
                # 显示最近的所有POST请求
                recent_posts = [req for req in all_requests[-10:] if req['method'].upper() == 'POST']
                if recent_posts:
                    logger.info("\n📮 最近的POST请求:")
                    for req in recent_posts:
                        logger.info(f"  {req['method']} {req['url']}")
                        if req['post_data']:
                            logger.info(f"     数据: {req['post_data'][:200]}...")
                
        except Exception as e:
            logger.error(f"❌ 调试过程中出错: {e}")
            
        finally:
            input("按Enter键关闭浏览器...")
            browser.close()

if __name__ == "__main__":
    debug_all_network_requests() 