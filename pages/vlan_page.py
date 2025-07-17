# VLAN页面类
from pages.base_page import BasePage
from playwright.sync_api import Page
import time
from utils.yaml_reader import YamlReader
from utils.constants import DOWNLOAD_DIR
from pathlib import Path
import json

class VlanPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        
        # VLAN页面元素选择器
        self.network_settings_text = "网络设置"
        self.vlan_settings_link = "VLAN设置"
        self.add_link = "添加"
        self.save_button_role = ("button", "保存")
        
        # VLAN表单字段
        self.vlan_id_input = "input[name='vlan_id']"
        self.vlan_name_input = "input[name='vlan_name']"
        self.ip_addr_input = "input[name='ip_addr']"
        self.comment_input = "input[name='comment']"
        
        # 搜索功能相关元素
        self.search_input = "input[placeholder*='VlanID/Vlan名称/IP/备注']"
        self.search_input_alt = "input[type='text']"  # 备用选择器
        self.search_clear_btn = "button[aria-label='Clear']"
        self.search_button_role = ("button", "")  # 搜索按钮（空文本）
        
    def _setup_vlan_api_listener(self, operation_name: str = "unknown", filter_actions: list[str] | None = None):
        """设置VLAN API监听器，返回监听器函数和结果容器
        
        Args:
            operation_name: 操作名称
            filter_actions: 需要过滤的action列表，如['up', 'down']，None表示捕获所有
        """
        matched_calls: list = []
        
        def _hook(req):
            # 调试：记录所有POST请求
            if req.method.lower() == "post":
                self.logger.debug(f"[调试] POST请求: {req.url}")
                if req.post_data:
                    self.logger.debug(f"[调试] 请求体: {req.post_data[:200]}...")  # 只显示前200个字符
            
            # 只处理 POST /Action/call
            if req.method.lower() != "post" or "/action/call" not in req.url.lower():
                return

            body = (req.post_data or "").lower()
            self.logger.debug(f"[调试] Action/call请求体: {body}")
            
            # func_name=vlan
            if "\"func_name\":\"vlan\"" in body:
                # 解析 action 字段 (add / show / edit / up / down / EXPORT / IMPORT ...)
                action_val = "unknown"
                import re
                # 支持大小写字母、数字、下划线
                m = re.search(r'"action"\s*:\s*"([A-Za-z0-9_]+)"', body)
                if m:
                    action_val = m.group(1).lower()  # 统一转为小写

                # 如果设置了过滤器，只处理指定的action
                if filter_actions and action_val not in filter_actions:
                    return

                # 获取响应（如果可用）
                try:
                    resp_obj = req.response()
                except:
                    resp_obj = None

                matched_calls.append({
                    "action": action_val,
                    "req": req,
                    "resp": resp_obj
                })
                
                # 输出调试信息（只有在没有过滤器或符合过滤条件时才输出）
                if not filter_actions or action_val in filter_actions:
                    self.logger.info(f"🎯 [全局监听] 捕获到VLAN API: action={action_val}")
                    self.logger.info(f"🎯 [全局监听] 请求体: {req.post_data}")
                    try:
                        if resp_obj:
                            resp_data = resp_obj.json()
                            self.logger.info(f"🎯 [全局监听] 响应: {resp_data}")
                        else:
                            self.logger.info(f"🎯 [全局监听] 响应未就绪")
                    except:
                        if resp_obj:
                            self.logger.info(f"🎯 [全局监听] 响应状态: {resp_obj.status}")
                        else:
                            self.logger.info(f"🎯 [全局监听] 响应解析失败")
                
                
                # 保存API记录 - 支持所有VLAN操作
                try:
                    from utils.api_recorder import save_api_call
                    
                    if resp_obj:
                        # 根据action类型和操作名称生成文件名
                        if action_val == "add":
                            # 尝试从请求体中提取vlan_id
                            vlan_id = "unknown"
                            try:
                                import json
                                body_json = json.loads(req.post_data or "{}")
                                vlan_id = body_json.get("param", {}).get("vlan_id", "unknown")
                            except:
                                pass
                            filename = f"add_vlan_{vlan_id}"
                        elif action_val == "show":
                            filename = f"show_vlan_{operation_name}"
                        elif action_val == "up":
                            filename = f"enable_vlan_{operation_name}"
                        elif action_val == "down":
                            filename = f"disable_vlan_{operation_name}"
                        elif action_val == "export":
                            filename = f"export_vlan_{operation_name}"
                        elif action_val == "import":
                            filename = f"import_vlan_{operation_name}"
                        elif action_val == "del":
                            filename = f"delete_vlan_{operation_name}"
                        else:
                            filename = f"{action_val}_vlan_{operation_name}"
                        
                        json_path, curl_path = save_api_call(filename, req, resp_obj, use_timestamp=False)
                        self.logger.info(f"[API-{action_val.upper()}] JSON: {json_path}")
                        self.logger.info(f"[API-{action_val.upper()}] CURL: {curl_path}")
                    else:
                        self.logger.warning(f"响应未就绪，无法保存API记录: {action_val}")
                except Exception as e:
                    self.logger.warning(f"保存 API 记录失败: {e}")
        
        return _hook, matched_calls
        
    def _cleanup_api_listener(self, hook_func):
        """清理API监听器"""
        try:
            # Playwright Python版本使用remove_listener
            self.page.remove_listener("requestfinished", hook_func)  # type: ignore
            self.logger.info("[API监听] 已清理API监听器")
        except Exception as e:
            self.logger.warning(f"清理API监听器失败: {e}")
        
    def navigate_to_vlan_page(self):
        """导航到VLAN设置页面"""
        try:
            self.logger.info("导航到VLAN设置页面")
            
            # 等待页面加载
            time.sleep(2)
            
            # 点击网络设置菜单
            if not self.click_text_filter(self.network_settings_text):
                self.logger.error("无法找到网络设置菜单")
                return False
                
            # 等待子菜单展开
            time.sleep(1)
                
            # 点击VLAN设置链接
            if not self.click_link_by_text(self.vlan_settings_link):
                self.logger.error("无法找到VLAN设置链接")
                return False
                
            # 等待页面加载
            time.sleep(3)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.logger.info("成功导航到VLAN设置页面")
            return True
            
        except Exception as e:
            self.logger.error(f"导航到VLAN页面失败: {e}")
            self.screenshot.take_screenshot("vlan_navigation_error")
            return False
            
    def add_vlan(self, vlan_id: str, vlan_name: str, ip_addr: str, comment: str = ""):
        """添加VLAN"""
        try:
            self.logger.info(f"开始添加VLAN: ID={vlan_id}, Name={vlan_name}")
            
            # 导航到VLAN页面
            if not self.navigate_to_vlan_page():
                return False
                
            # 点击添加按钮
            if not self.click_link_by_text(self.add_link):
                self.logger.error("无法找到添加按钮")
                return False
                
            # 等待表单加载
            time.sleep(2)
            
            # 填写VLAN ID
            if not self.input_text(self.vlan_id_input, vlan_id):
                self.logger.error("无法输入VLAN ID")
                return False
                
            # 填写VLAN名称
            if not self.input_text(self.vlan_name_input, vlan_name):
                self.logger.error("无法输入VLAN名称")
                return False
                
            # 填写IP地址
            if not self.input_text(self.ip_addr_input, ip_addr):
                self.logger.error("无法输入IP地址")
                return False
                
            # 填写备注（可选）
            if comment:
                if not self.input_text(self.comment_input, comment):
                    self.logger.warning("无法输入备注，但继续执行")
                
            # *** -------------- 改用全局监听捕获 VLAN 新增接口 -------------- ***
            # 1) 注册一次性监听
            matched_calls: list = []  # 保存多个接口（add、show）

            def _hook(req):
                # 只处理 POST /Action/call
                if req.method.lower() != "post" or "/action/call" not in req.url.lower():
                    return

                body = (req.post_data or "").lower()
                # func_name=vlan
                if "\"func_name\":\"vlan\"" in body:
                    # 解析 action 字段 (add / show / edit ...)
                    action_val = "unknown"
                    import re
                    m = re.search(r'"action"\s*:\s*"(\w+)"', body)
                    if m:
                        action_val = m.group(1)

                    matched_calls.append({
                        "action": action_val,
                        "req": req,
                        "resp": req.response()
                    })

            self.page.on("requestfinished", _hook)

            # 2) 点击保存按钮
            if not self.click_by_role(self.save_button_role[0], self.save_button_role[1]):
                self.logger.error("无法点击保存按钮")
                self.page.off("requestfinished", _hook)
                return False

            # 3) 等待结果（最多 5s，每 0.1s 轮询）
            for _ in range(60):  # 最长 6 秒
                # 若已经捕获到 add 和 show 则提前结束
                actions = [c["action"] for c in matched_calls]
                if "add" in actions and "show" in actions:
                    break
                self.page.wait_for_timeout(100)

            # 4) 解绑监听
            self.page.remove_listener("requestfinished", _hook)  # type: ignore

            # 提取 add/show 调用
            add_call = next((c for c in matched_calls if c["action"] == "add"), None)
            show_call = next((c for c in matched_calls if c["action"] == "show"), None)

            if add_call:
                req_obj = add_call["req"]
                resp_obj = add_call["resp"]
                try:
                    resp_json = resp_obj.json()
                except Exception:
                    resp_json = None

                self.logger.info(f"后台接口返回成功: {resp_json}")
                try:
                    self.logger.info(f"[API-REQ-Header] {json.dumps(dict(req_obj.headers), ensure_ascii=False)}")
                    self.logger.info(f"[API-REQ-Body] {req_obj.post_data}")
                    self.logger.info(f"[API-RESP-Header] {json.dumps(dict(resp_obj.headers), ensure_ascii=False)}")
                except Exception:
                    pass

                # 保存文件 (add)
                try:
                    from utils.api_recorder import save_api_call
                    json_path, curl_path = save_api_call(f"add_vlan_{vlan_id}", req_obj, resp_obj, use_timestamp=False)
                    self.logger.info(f"[API] 已保存至: {json_path}")
                    self.logger.info(f"[CURL] 已保存至: {curl_path}")
                except Exception as e:
                    self.logger.warning(f"保存 API 记录失败: {e}")

                api_success = True

                # 如果存在 show 接口，同样记录一次（可选）
                if show_call:
                    s_req = show_call["req"]; s_resp = show_call["resp"]
                    try:
                        self.logger.info(f"后台列表刷新接口返回: {s_resp.json()}")
                        self.logger.info(f"[API-REQ-Body-SHOW] {s_req.post_data}")
                    except Exception:
                        pass

                    try:
                        from utils.api_recorder import save_api_call
                        json_path, curl_path = save_api_call(f"show_vlan_after_add_{vlan_id}", s_req, s_resp, use_timestamp=False)
                        self.logger.info(f"[API-SHOW] 已保存至: {json_path}")
                    except Exception:
                        pass

            else:
                self.logger.error("未捕获到 VLAN 新增接口")
                api_success = False
            

            # 等待保存结果
            time.sleep(3)
            self.page.wait_for_load_state("networkidle", timeout=10000)

            # 检查是否保存成功 (UI Toast)
            message = self.wait_for_toast_message()
            if api_success:
                # API 已确认成功，忽略 Toast
                self.logger.info(f"VLAN 添加成功(接口校验): {vlan_name}")
                return True
            elif message and ("成功" in message or "保存" in message):
                self.logger.info(f"VLAN 添加成功(Toast): {vlan_name}")
                return True
            else:
                self.logger.error(f"VLAN 添加失败: 未捕获成功提示且接口校验失败")
                return False
                
        except Exception as e:
            self.logger.error(f"添加VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_add_error")
            return False
            
    def add_vlan_with_partial_fields(self, vlan_id: str = None, vlan_name: str = None, ip_addr: str = None, comment: str = None):
        """支持部分字段为空的添加VLAN方法（用于异常校验）"""
        try:
            self.logger.info(f"开始异常场景添加VLAN: ID={vlan_id}, Name={vlan_name}")
            if not self.navigate_to_vlan_page():
                return False
            if not self.click_link_by_text(self.add_link):
                self.logger.error("无法找到添加按钮")
                return False
            time.sleep(2)
            # VLAN ID
            if vlan_id is not None:
                self.input_text(self.vlan_id_input, vlan_id)
            # VLAN名称
            if vlan_name is not None:
                self.input_text(self.vlan_name_input, vlan_name)
            # IP地址
            if ip_addr is not None:
                self.input_text(self.ip_addr_input, ip_addr)
            # 备注
            if comment is not None:
                self.input_text(self.comment_input, comment)
            # 点击保存
            self.click_by_role(self.save_button_role[0], self.save_button_role[1])
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"异常场景添加VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_add_required_error")
            return False

    def get_required_field_message(self, field_text: str):
        """获取字段必填提示信息，返回 True/False"""
        try:
            # 等待提示元素出现在 DOM，超时 3 秒
            try:
                self.page.wait_for_selector(f"text={field_text}", timeout=3000)
            except Exception:
                pass  # 不抛出，继续模糊匹配

            # 1) 首先尝试完整文案匹配（不要求可见，只要存在即可）
            if self.page.locator(f"text={field_text}").count() > 0:
                return True

            # 2) 回退：只用句首 5~8 个关键字匹配
            keyword = field_text[:6]  # e.g. "整数范围"
            try:
                locs2 = self.page.locator(f"text={keyword}")
                for i in range(locs2.count()):
                    if locs2.nth(i).is_visible():
                        return True
            except Exception:
                pass

            # 3) 通过常见错误提示类名查找
            try:
                tip_locs = self.page.locator("p.error_tip")
                for i in range(tip_locs.count()):
                    txt = tip_locs.nth(i).text_content() or ""
                    if keyword in txt:
                        return True
            except Exception:
                pass

            # 4) 最终回退：使用 XPath contains 任意元素匹配
            try:
                xpath_loc = self.page.locator(f"xpath=//*[contains(text(), '{keyword}')]")
                for i in range(xpath_loc.count()):
                    if xpath_loc.nth(i).is_visible():
                        return True
            except Exception:
                pass

            return False
        except Exception as e:
            self.logger.error(f"获取必填提示信息失败: {e}")
            return False
            
    def get_vlan_list(self):
        """获取VLAN列表"""
        try:
            # 确保在VLAN页面
            if not self.navigate_to_vlan_page():
                return []
                
            # 等待表格加载
            time.sleep(2)
            self.page.wait_for_load_state("networkidle", timeout=5000)
            
            # 查找VLAN表格
            table_selectors = [
                "table tbody tr",
                ".vlan-table tbody tr", 
                ".ant-table tbody tr",
                ".el-table tbody tr",
                "[class*='table'] tbody tr"
            ]
            
            vlans = []
            for selector in table_selectors:
                try:
                    rows = self.page.query_selector_all(selector)
                    if rows:
                        for row in rows:
                            cells = row.query_selector_all("td")
                            if len(cells) >= 4:  # 确保有足够的列
                                # 根据表格结构：vlanID | vlan名称 | MAC | IP | 子网掩码 | 线路 | 备注 | 状态 | 操作
                                vlan_data = {
                                    'id': (cells[0].text_content() or "").strip() if len(cells) > 0 else "",
                                    'name': (cells[1].text_content() or "").strip() if len(cells) > 1 else "",
                                    'mac': (cells[2].text_content() or "").strip() if len(cells) > 2 else "",
                                    'ip': (cells[3].text_content() or "").strip() if len(cells) > 3 else "",
                                    'subnet_mask': (cells[4].text_content() or "").strip() if len(cells) > 4 else "",
                                    'line': (cells[5].text_content() or "").strip() if len(cells) > 5 else "",
                                    'comment': (cells[6].text_content() or "").strip() if len(cells) > 6 else "",
                                    'status': (cells[7].text_content() or "").strip() if len(cells) > 7 else ""
                                }
                                # 过滤掉空行
                                if vlan_data['id'] or vlan_data['name']:
                                    vlans.append(vlan_data)
                        break
                except:
                    continue
                    
            self.logger.info(f"获取到VLAN列表，共 {len(vlans)} 条记录")
            
            # 调试输出：显示解析的数据结构
            if vlans:
                sample_vlan = vlans[0]
                self.logger.debug(f"VLAN数据结构示例: {sample_vlan}")
            
            return vlans
            
        except Exception as e:
            self.logger.error(f"获取VLAN列表失败: {e}")
            return []
            
    def delete_vlan(self, vlan_id: str):
        """删除VLAN"""
        try:
            self.logger.info(f"开始删除VLAN: {vlan_id}")
            
            # 确保在VLAN页面
            if not self.navigate_to_vlan_page():
                return False
                
            # 查找删除按钮（通常在表格行中）
            delete_selectors = [
                f"[data-vlan-id='{vlan_id}'] .delete-btn",
                f"tr:has-text('{vlan_id}') .delete",
                f"tr:has-text('{vlan_id}') button:has-text('删除')",
                f"text=删除"
            ]
            
            for selector in delete_selectors:
                try:
                    if self.is_element_visible(selector):
                        if self.click_element(selector):
                            # 确认删除
                            time.sleep(1)
                            confirm_selectors = [
                                "button:has-text('确认')",
                                "button:has-text('确定')", 
                                ".ant-btn-primary",
                                ".el-button--primary"
                            ]
                            
                            for confirm_selector in confirm_selectors:
                                if self.is_element_visible(confirm_selector):
                                    self.click_element(confirm_selector)
                                    break
                                    
                            # 等待删除结果
                            time.sleep(2)
                            message = self.wait_for_toast_message()
                            if message and "成功" in message:
                                self.logger.info(f"VLAN删除成功: {vlan_id}")
                                return True
                            else:
                                self.logger.info(f"VLAN删除完成（未找到确认消息）: {vlan_id}")
                                return True
                            break
                except:
                    continue
                    
            self.logger.error(f"未找到VLAN删除按钮: {vlan_id}")
            return False
            
        except Exception as e:
            self.logger.error(f"删除VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_delete_error")
            return False
        
    def add_extend_ip(self, ip: str, mask: str = None):
        """添加扩展IP（支持掩码选择）"""
        try:
            self.logger.info(f"添加扩展IP: {ip} {mask if mask else ''}")
            # 点击"添加"按钮（扩展IP区域）
            self.page.get_by_role("link", name="添加").click()
            time.sleep(1)
            # 输入扩展IP
            self.page.locator("input[name='ip']").fill(ip)
            # 选择掩码（如果有）
            if mask:
                try:
                    self.page.locator("select[name='mask']").select_option(label=mask)
                except Exception:
                    pass  # 掩码不是select时可忽略
                time.sleep(0.5)
            # 点击"确定"按钮（在弹窗或下拉菜单内）
            self.page.locator("#fantasyMenu").get_by_text("确定").click()
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"添加扩展IP出错: {e}")
            self.screenshot.take_screenshot("extend_ip_add_error")
            return False

    def is_extend_ip_in_table(self, ip: str):
        """判断扩展IP是否已在表格中"""
        try:
            return self.page.get_by_role("cell", name=ip).is_visible()
        except Exception as e:
            self.logger.error(f"扩展IP表格校验失败: {e}")
            return False
        
    def enable_vlan(self, vlan_id: str):
        """单个VLAN启用（不抓取API）"""
        try:
            self.logger.info(f"启用VLAN: {vlan_id}")
            self.navigate_to_vlan_page()
            time.sleep(2)  # 确保页面完全加载
            
            rows = self.page.query_selector_all("table tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if cells and cells[0].text_content() and cells[0].text_content().strip() == str(vlan_id):
                    btns = row.query_selector_all("a")
                    for btn in btns:
                        if btn.text_content() and btn.text_content().strip() == "启用":
                            self.logger.info(f"🎯 找到启用按钮，准备点击...")
                            btn.click()
                            self.logger.info(f"✅ 已点击启用按钮")
                            time.sleep(2)  # 等待操作完成
                            return True
            
            self.logger.error(f"未找到VLAN{vlan_id}的启用按钮")
            return False
        except Exception as e:
            self.logger.error(f"启用VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_enable_error")
            return False

    def enable_all_vlans(self):
        """全部启用VLAN（抓取批量启用API）- 使用全局监听"""
        try:
            self.logger.info("全部启用VLAN")
            
            # 设置全局API监听器，只过滤up操作
            hook_func, matched_calls = self._setup_vlan_api_listener("enable_all", filter_actions=["up"])
            self.page.on("requestfinished", hook_func)
            self.logger.info("[API监听] 已设置全局启用VLAN的API监听器")
            
            # 导航到VLAN页面
            self.navigate_to_vlan_page()
            time.sleep(2)  # 确保页面完全加载
            
            # 点击表头全选复选框
            checkbox = self._find_select_all_checkbox()
            if not checkbox:
                self.logger.error("未找到表头全选复选框")
                self._cleanup_api_listener(hook_func)
                return False
            
            self.logger.info("🎯 准备点击全选复选框...")
            checkbox.click()
            self.logger.info("✅ 已点击全选复选框")
            time.sleep(1)
            
            # 点击批量启用按钮
            self.logger.info("🎯 准备点击批量启用按钮...")
            self.page.get_by_role("link", name="启用").click()
            self.logger.info("✅ 已点击批量启用按钮，等待API调用...")
            
            # 等待API调用被捕获 - 专门等待up接口
            up_api_found = False
            for i in range(150):  # 等待15秒，每100ms检查一次
                if matched_calls:
                    actions = [c['action'] for c in matched_calls]
                    if 'up' in actions:
                        self.logger.info(f"🎉 检测到批量启用API调用 (第{i+1}次检查): {actions}")
                        up_api_found = True
                        break
                    elif i % 10 == 0:  # 每秒输出一次进度
                        self.logger.info(f"⏳ 等待启用API调用... (第{i+1}次检查，已捕获: {actions})")
                time.sleep(0.1)
            
            # 如果还没找到up接口，再等待5秒
            if not up_api_found:
                self.logger.info("⏳ 继续等待5秒以捕获延迟的启用API调用...")
                for i in range(50):  # 再等待5秒
                    if matched_calls:
                        actions = [c['action'] for c in matched_calls]
                        if 'up' in actions:
                            self.logger.info(f"🎉 检测到延迟的批量启用API调用: {actions}")
                            up_api_found = True
                            break
                    time.sleep(0.1)
            
            if not up_api_found:
                self.logger.warning("⚠️ 等待20秒后仍未检测到批量启用(up)API调用")
                # 显示捕获到的所有API调用
                if matched_calls:
                    all_actions = [c['action'] for c in matched_calls]
                    self.logger.warning(f"实际捕获到的API调用: {all_actions}")
            
            # 等待额外时间确保所有API调用都被捕获
            self.logger.info("⏳ 等待额外2秒以确保所有延迟的API调用都被捕获...")
            time.sleep(2)
            
            self._cleanup_api_listener(hook_func)
            return True
            
        except Exception as e:
            self.logger.error(f"全部启用VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_enable_all_error")
            self._cleanup_api_listener(hook_func)
            return False
            
    def disable_vlan(self, vlan_id: str):
        """单个VLAN停用（不抓取API）"""
        try:
            self.logger.info(f"停用VLAN: {vlan_id}")
            self.navigate_to_vlan_page()
            time.sleep(2)  # 确保页面完全加载
            
            rows = self.page.query_selector_all("table tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if cells and cells[0].text_content() and cells[0].text_content().strip() == str(vlan_id):
                    btns = row.query_selector_all("a")
                    for btn in btns:
                        if btn.text_content() and btn.text_content().strip() == "停用":
                            self.logger.info(f"🎯 找到停用按钮，准备点击...")
                            btn.click()
                            self.logger.info(f"✅ 已点击停用按钮")
                            time.sleep(2)  # 等待操作完成
                            return True
            
            self.logger.error(f"未找到VLAN{vlan_id}的停用按钮")
            return False
        except Exception as e:
            self.logger.error(f"停用VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_disable_error")
            return False

    def disable_all_vlans(self):
        """全部停用VLAN（抓取批量停用API）- 使用全局监听"""
        try:
            self.logger.info("全部停用VLAN")
            
            # 设置全局API监听器，只过滤down操作
            hook_func, matched_calls = self._setup_vlan_api_listener("disable_all", filter_actions=["down"])
            self.page.on("requestfinished", hook_func)
            self.logger.info("[API监听] 已设置全局停用VLAN的API监听器")
            
            # 导航到VLAN页面
            self.navigate_to_vlan_page()
            time.sleep(2)  # 确保页面完全加载
            
            # 点击表头全选复选框
            checkbox = self._find_select_all_checkbox()
            if not checkbox:
                self.logger.error("未找到表头全选复选框")
                self._cleanup_api_listener(hook_func)
                return False
            
            self.logger.info("🎯 准备点击全选复选框...")
            checkbox.click()
            self.logger.info("✅ 已点击全选复选框")
            time.sleep(1)
            
            # 点击批量停用按钮
            self.logger.info("🎯 准备点击批量停用按钮...")
            self.page.get_by_role("link", name="停用").click()
            self.logger.info("✅ 已点击批量停用按钮，等待API调用...")
            
            # 等待API调用被捕获 - 专门等待down接口
            down_api_found = False
            for i in range(150):  # 等待15秒，每100ms检查一次
                if matched_calls:
                    actions = [c['action'] for c in matched_calls]
                    if 'down' in actions:
                        self.logger.info(f"🎉 检测到批量停用API调用 (第{i+1}次检查): {actions}")
                        down_api_found = True
                        break
                    elif i % 10 == 0:  # 每秒输出一次进度
                        self.logger.info(f"⏳ 等待停用API调用... (第{i+1}次检查，已捕获: {actions})")
                time.sleep(0.1)
            
            # 如果还没找到down接口，再等待5秒
            if not down_api_found:
                self.logger.info("⏳ 继续等待5秒以捕获延迟的停用API调用...")
                for i in range(50):  # 再等待5秒
                    if matched_calls:
                        actions = [c['action'] for c in matched_calls]
                        if 'down' in actions:
                            self.logger.info(f"🎉 检测到延迟的批量停用API调用: {actions}")
                            down_api_found = True
                            break
                    time.sleep(0.1)
            
            if not down_api_found:
                self.logger.warning("⚠️ 等待20秒后仍未检测到批量停用(down)API调用")
                # 显示捕获到的所有API调用
                if matched_calls:
                    all_actions = [c['action'] for c in matched_calls]
                    self.logger.warning(f"实际捕获到的API调用: {all_actions}")
            
            # 等待额外时间确保所有API调用都被捕获
            self.logger.info("⏳ 等待额外2秒以确保所有延迟的API调用都被捕获...")
            time.sleep(2)
            
            self._cleanup_api_listener(hook_func)
            return True
            
        except Exception as e:
            self.logger.error(f"全部停用VLAN出错: {e}")
            self.screenshot.take_screenshot("vlan_disable_all_error")
            self._cleanup_api_listener(hook_func)
            return False

    def _find_select_all_checkbox(self):
        """只用Playwright录制方式查找表头全选复选框"""
        try:
            checkbox = self.page.get_by_role("row", name="vlanID vlan名称 MAC IP").locator("label span")
            if checkbox.count() > 0 and checkbox.first.is_visible():
                return checkbox.first
        except Exception:
            pass
        return None

    def batch_enable_vlans(self, vlan_ids: list[str] | None = None, select_all: bool = False):
        """批量启用VLAN（兼容旧接口，推荐使用enable_all_vlans）"""
        if select_all or not vlan_ids:
            return self.enable_all_vlans()
        
        try:
            self.logger.info(f"批量启用指定VLAN: {vlan_ids}")
            
            # 设置API监听
            hook_func, matched_calls = self._setup_vlan_api_listener(f"batch_enable_{len(vlan_ids)}")
            self.page.on("requestfinished", hook_func)
            
            self.navigate_to_vlan_page()
            time.sleep(1)
            
            # 选择指定的VLAN
            for vid in vlan_ids:
                self.page.get_by_role("row", name=vid).locator(".td_check").click()
            
            # 点击批量启用按钮
            self.page.get_by_role("link", name="启用").click()
            
            # 等待API调用被捕获
            for i in range(100):  # 等待10秒
                if matched_calls:
                    self.logger.info(f"🎉 检测到批量启用API调用: {[c['action'] for c in matched_calls]}")
                    break
                time.sleep(0.1)
            
            time.sleep(2)  # 等待操作完成
            self._cleanup_api_listener(hook_func)
            return True
        except Exception as e:
            self.logger.error(f"批量启用VLAN出错: {e}")
            self.screenshot.take_screenshot("batch_vlan_enable_error")
            self._cleanup_api_listener(hook_func)
            return False

    def batch_disable_vlans(self, vlan_ids: list[str] | None = None, select_all: bool = False):
        """批量停用VLAN（兼容旧接口，推荐使用disable_all_vlans）"""
        if select_all or not vlan_ids:
            return self.disable_all_vlans()
        
        try:
            self.logger.info(f"批量停用指定VLAN: {vlan_ids}")
            
            # 设置API监听
            hook_func, matched_calls = self._setup_vlan_api_listener(f"batch_disable_{len(vlan_ids)}")
            self.page.on("requestfinished", hook_func)
            
            self.navigate_to_vlan_page()
            time.sleep(1)
            
            # 选择指定的VLAN
            for vid in vlan_ids:
                self.page.get_by_role("row", name=vid).locator(".td_check").click()
            
            # 点击批量停用按钮
            self.logger.info("🎯 准备点击批量停用按钮...")
            self.page.get_by_role("link", name="停用").click()
            self.logger.info("✅ 已点击批量停用按钮，等待API调用...")
            
            # 等待API调用被捕获
            for i in range(100):  # 等待10秒
                if matched_calls:
                    self.logger.info(f"🎉 检测到批量停用API调用: {[c['action'] for c in matched_calls]}")
                    break
                time.sleep(0.1)
            else:
                self.logger.warning("⚠️ 等待10秒后仍未检测到批量停用API调用")
            
            # 等待额外时间确保所有API调用都被捕获
            time.sleep(2)
            self._cleanup_api_listener(hook_func)
            return True
        except Exception as e:
            self.logger.error(f"批量停用VLAN出错: {e}")
            self.screenshot.take_screenshot("batch_vlan_disable_error")
            self._cleanup_api_listener(hook_func)
            return False

    def get_vlan_status(self, vlan_id: str):
        """获取VLAN当前状态（已启用/已停用）"""
        try:
            row = self.page.get_by_role("row", name=vlan_id)
            # 状态列为第8列（索引7）
            status = row.locator("td").nth(7).text_content().strip()
            return status
        except Exception as e:
            self.logger.error(f"获取VLAN状态失败: {e}")
            return None

    def get_all_vlan_status(self):
        """获取所有VLAN的状态，返回dict: {vlan_id: status}"""
        try:
            result = {}
            rows = self.page.query_selector_all("table tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) >= 8:
                    vid = cells[0].text_content().strip()
                    status = cells[7].text_content().strip()
                    result[vid] = status
            return result
        except Exception as e:
            self.logger.error(f"获取所有VLAN状态失败: {e}")
            return {}

    # 新增: 导出配置文件
    def export_vlan(self, fmt: str = "csv") -> Path:
        """点击导出按钮并保存文件到项目 exports 目录

        Args:
            fmt: "csv" 或 "txt"
        Returns: 保存后的文件 Path，失败返回 None
        """
        fmt = fmt.lower()
        if fmt not in {"csv", "txt"}:
            raise ValueError("格式必须是 csv 或 txt")

        # 先确保已在 VLAN 页面
        if not self.navigate_to_vlan_page():
            self.logger.error("无法进入VLAN页面，导出操作中止")
            return None

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = f"vlan_backup_{timestamp}.{fmt}"
        target_path = DOWNLOAD_DIR / file_name

        # 设置API监听
        hook_func, matched_calls = self._setup_vlan_api_listener(f"export_{fmt}")
        self.page.on("requestfinished", hook_func)

        try:
            with self.page.expect_download() as dl_info:
                # 1. 触发导出下拉
                export_btn = self.page.get_by_role("link", name="导出")
                if not export_btn.count():
                    export_btn = self.page.get_by_role("button", name="导出")

                if export_btn.count():
                    try:
                        # 先 hover 再点击，兼容 hover 弹出菜单 / 点击弹出菜单 两种模式
                        export_btn.first.hover()
                    except Exception:
                        pass
                    try:
                        export_btn.first.click()
                    except Exception:
                        # 有些界面 hover 已经弹出，无需点击
                        pass

                # 2. 点击具体格式（CSV / TXT）。使用多种定位方式保证稳健
                format_clicked = False
                candidate_locators = [
                    self.page.get_by_role("link", name=fmt.upper()),
                    self.page.get_by_role("menuitem", name=fmt.upper()),
                    self.page.get_by_role("option", name=fmt.upper()),
                    self.page.locator(f"text={fmt.upper()}")
                ]
                for loc in candidate_locators:
                    try:
                        if loc.count() and loc.first.is_visible():
                            loc.first.click()
                            format_clicked = True
                            break
                    except Exception:
                        continue

                if not format_clicked:
                    raise Exception(f"未找到 {fmt.upper()} 导出选项")

            download = dl_info.value  # type: ignore
            download.save_as(str(target_path))
            self.logger.info(f"成功导出{fmt.upper()}文件: {target_path.name}")
            
            # 等待API调用完成
            time.sleep(2)
            self._cleanup_api_listener(hook_func)
            return target_path
        except Exception as e:
            self.logger.error(f"导出{fmt}失败: {e}")
            self._cleanup_api_listener(hook_func)
            return None

    def import_vlan(self, file_path: Path, fmt: str = "csv", merge: bool = False) -> bool:
        """导入VLAN配置

        Args:
            file_path: 要导入的文件路径
            fmt: csv / txt
            merge: 是否勾选"合并到当前数据"
        """
        if not file_path.exists():
            self.logger.error(f"文件不存在: {file_path}")
            return False

        # 确保位于 VLAN 页面
        if not self.navigate_to_vlan_page():
            self.logger.error("无法进入VLAN页面，导入操作中止")
            return False

        # 设置API监听
        hook_func, matched_calls = self._setup_vlan_api_listener(f"import_{fmt}")
        self.page.on("requestfinished", hook_func)

        try:
            # 点击导入按钮
            self.page.get_by_role("link", name="导入").click()
            time.sleep(1) # 等待导入按钮点击生效

            # 定位文件输入框并设置文件
            file_input = self.page.locator("input[type=file]")
            if file_input.count() and file_input.first.is_visible():
                file_input.first.set_input_files(str(file_path))
            else:
                self.logger.error("未找到文件输入框")
                return False

            # 处理合并复选框（如存在）
            if merge:
                merged = False
                # 1) 标准 role 定位
                try:
                    checkbox = self.page.get_by_role("checkbox", name="合并到当前数据")
                    if checkbox.count():
                        if not checkbox.first.is_checked():
                            checkbox.first.check()
                        merged = True
                except Exception:
                    pass

                # 2) 回退：通过 label 文本再点击内部 <span>
                if not merged:
                    try:
                        span = self.page.locator("label").filter(has_text="合并到当前数据").locator("span")
                        if span.count():
                            # 判断是否已勾选（class 中包含 checked）
                            cls = span.first.get_attribute("class") or ""
                            if "checked" not in cls and "is-checked" not in cls:
                                span.first.click()
                            merged = True
                    except Exception:
                        pass

                if not merged:
                    self.logger.warning("未找到 \"合并到当前数据\" 复选框，可能 UI 更新")

            # 点击确定/上传按钮
            try:
                # 先尝试常见按钮文本
                confirm_btn = self.page.get_by_role("button", name="确定")
                if not confirm_btn.count():
                    confirm_btn = self.page.get_by_role("button", name="确认导入")
                if not confirm_btn.count():
                    confirm_btn = self.page.get_by_role("button", name="上传")

                if confirm_btn.count():
                    confirm_btn.first.click()
                else:
                    # 最后回退纯文本匹配
                    self.page.locator("button:has-text('确定')").first.click()
            except:
                pass

            time.sleep(3)  # 等待导入完成
            self.logger.info(f"已导入文件: {file_path.name}")
            self._cleanup_api_listener(hook_func)
            return True
        except Exception as e:
            self.logger.error(f"导入失败: {e}")
            self._cleanup_api_listener(hook_func)
            return False

    def delete_all_vlans(self) -> bool:
        """批量删除所有现有 VLAN 配置"""
        try:
            # 确保在 VLAN 页面
            if not self.navigate_to_vlan_page():
                self.logger.error("无法进入VLAN页面，批量删除操作中止")
                return False

            # 设置API监听
            hook_func, matched_calls = self._setup_vlan_api_listener("delete_all")
            self.page.on("requestfinished", hook_func)

            # 1. 勾选表头全选复选框（优先使用 _find_select_all_checkbox，兼容不同 DOM）
            header_checkbox = self._find_select_all_checkbox()
            if header_checkbox:
                header_checkbox.click()
            else:
                header_cb = self.page.locator('thead input[type="checkbox"]')
                if header_cb.count():
                    if not header_cb.first.is_checked():
                        header_cb.first.check()
                else:
                    self.logger.warning("未找到表头全选复选框，可能页面结构变更")

            time.sleep(1)
            # 点击 删除 按钮
            delete_btns = self.page.get_by_role("link", name="删除")
            if delete_btns.count() == 0:
                delete_btns = self.page.get_by_role("button", name="删除")
            if delete_btns.count() == 0:
                self.logger.warning("未找到批量删除按钮")
                return False

            delete_btns.first.click()
            # 确认对话框
            try:
                self.page.get_by_role("button", name="确定").click()
            except:
                pass

            time.sleep(3)
            self.logger.info("已批量删除所有 VLAN 配置")
            self._cleanup_api_listener(hook_func)
            return True
        except Exception as e:
            self.logger.error(f"删除所有VLAN失败: {e}")
            self._cleanup_api_listener(hook_func)
            return False

    def _wait_for_vlan_api_result(self, timeout: int = 10000):
        """等待 VLAN 相关接口响应并返回 (success, request_payload, response_json)"""
        try:
            def _is_vlan_call(r):
                try:
                    if r.request.method.upper() not in {"POST", "GET"}:
                        return False
                    post_data = r.request.post_data or ""
                    return "Vlan" in post_data or "Vlan" in r.url
                except Exception:
                    return False
 
            # 优先使用 wait_for_response，如果方法不存在或调用报错则回退
            wait_for_resp_func = getattr(self.page, "wait_for_response", None)
            if callable(wait_for_resp_func):
                try:
                    response = wait_for_resp_func(_is_vlan_call, timeout=timeout)
                except Exception:
                    response = self.page.wait_for_event("response", predicate=_is_vlan_call, timeout=timeout)
            else:
                response = self.page.wait_for_event("response", predicate=_is_vlan_call, timeout=timeout)
 
            # 解析请求载荷 (POST 数据可能是 JSON / form-data / urlencoded)
            request_payload = None
            try:
                post_data = response.request.post_data or ""
                if post_data:
                    # 尝试解析成 JSON, 解析失败则保留原字符串
                    try:
                        request_payload = json.loads(post_data)
                    except Exception:
                        request_payload = post_data
            except Exception:
                pass

            # 解析响应 JSON
            resp_json = None
            try:
                resp_json = response.json()
            except Exception:
                # 非 JSON 响应, 忽略
                pass

            # 记录日志
            self.logger.info(f"捕获 VLAN 接口请求: {request_payload}")
            self.logger.info(f"捕获 VLAN 接口响应: {resp_json}")

            # 判断成功
            if isinstance(resp_json, dict) and resp_json.get("Result") in [0, 30000]:
                return True, request_payload, resp_json
            else:
                # 返回非成功码，交由调用方判定
                return False, request_payload, resp_json

        except Exception as e:
            self.logger.warning(f"等待 VLAN 接口响应超时或失败: {e}")

            # 调试模式：捕获3秒内的所有响应，帮助定位
            self.logger.info("⚙️ 调试: 开始捕获所有接口响应 3 秒以分析…")
            captured = []
            def _all_resp_cb(r):
                try:
                    body = None
                    try:
                        body = r.json()
                    except Exception:
                        body = r.status
                    self.logger.info(f"[API] {r.request.method} {r.url} -> {r.status} {body}")
                    captured.append(r)
                except Exception:
                    pass

            self.page.on("response", _all_resp_cb)
            try:
                self.page.wait_for_timeout(3000)
            except Exception:
                time.sleep(3)
            if hasattr(self.page, "off"):
                self.page.off("response", _all_resp_cb)
            else:
                self.page.remove_listener("response", _all_resp_cb)

            self.logger.info(f"⚙️ 调试: 共捕获 {len(captured)} 条响应")
            return False, None, None
    
    def search_vlan(self, search_term: str):
        """在VLAN列表中搜索指定内容"""
        try:
            self.logger.info(f"开始搜索VLAN: {search_term}")
            
            # 确保在VLAN页面
            if not self.navigate_to_vlan_page():
                return False
                
            # 等待页面加载
            time.sleep(2)
            
            # 设置API监听器
            hook_func, matched_calls = self._setup_vlan_api_listener(f"search_{search_term}")
            self.page.on("requestfinished", hook_func)
            
            try:
                # 严格按照用户录制的代码执行三步操作
                self.logger.info("执行搜索操作 - 步骤1: 点击搜索框")
                
                # 步骤1: 点击搜索框
                search_box = self.page.get_by_role("textbox", name="vlanID/Vlan名称/IP/备注")
                if search_box.count() == 0:
                    self.logger.error("未找到搜索框")
                    return False
                    
                search_box.click()
                self.logger.info("✅ 已点击搜索框")
                time.sleep(0.5)  # 等待搜索框获得焦点
                
                # 步骤2: 输入搜索内容
                self.logger.info(f"执行搜索操作 - 步骤2: 输入搜索内容 '{search_term}'")
                if search_term:
                    search_box.fill(search_term)
                    self.logger.info(f"✅ 已在搜索框中输入: {search_term}")
                else:
                    search_box.clear()
                    self.logger.info("✅ 已清空搜索框")
                time.sleep(0.5)  # 等待输入完成
                
                # 步骤3: 点击搜索按钮（严格按照录制代码）
                self.logger.info("执行搜索操作 - 步骤3: 点击搜索按钮")
                
                # 首先尝试用户录制的精确方式
                search_buttons = self.page.get_by_role("button")
                if search_buttons.count() > 0:
                    # 查找搜索框附近的按钮
                    clicked = False
                    for i in range(search_buttons.count()):
                        try:
                            button = search_buttons.nth(i)
                            if button.is_visible():
                                # 尝试点击按钮
                                button.click()
                                self.logger.info(f"✅ 已点击搜索按钮 (第{i+1}个按钮)")
                                clicked = True
                                break
                        except Exception as e:
                            self.logger.debug(f"点击第{i+1}个按钮失败: {e}")
                            continue
                    
                    if not clicked:
                        self.logger.warning("所有按钮点击失败，尝试按回车键")
                        search_box.press("Enter")
                        self.logger.info("✅ 已按回车键执行搜索")
                else:
                    self.logger.warning("未找到搜索按钮，使用回车键")
                    search_box.press("Enter")
                    self.logger.info("✅ 已按回车键执行搜索")
                
                # 等待搜索结果更新
                time.sleep(2)
                self.page.wait_for_load_state("networkidle", timeout=5000)
                
                self.logger.info(f"✅ 搜索操作完成: {search_term}")
                return True
                
            except Exception as e:
                self.logger.error(f"搜索操作失败: {e}")
                self.screenshot.take_screenshot("search_vlan_error")
                return False
                    
            finally:
                # 清理API监听器
                self._cleanup_api_listener(hook_func)
            
        except Exception as e:
            self.logger.error(f"搜索VLAN失败: {e}")
            return False
    
    def get_filtered_vlan_list(self):
        """获取当前过滤后的VLAN列表"""
        try:
            # 等待搜索结果更新
            time.sleep(1)
            self.page.wait_for_load_state("networkidle", timeout=5000)
            
            # 查找VLAN表格
            table_selectors = [
                "table tbody tr",
                ".vlan-table tbody tr", 
                ".ant-table tbody tr",
                ".el-table tbody tr",
                "[class*='table'] tbody tr"
            ]
            
            vlans = []
            for selector in table_selectors:
                try:
                    rows = self.page.query_selector_all(selector)
                    if rows:
                        for row in rows:
                            # 检查行是否可见（未被搜索过滤掉）
                            if not row.is_visible():
                                continue
                                
                            cells = row.query_selector_all("td")
                            if len(cells) >= 2:
                                vlan_data = {
                                    'id': (cells[0].text_content() or "").strip() if len(cells) > 0 else "",
                                    'name': (cells[1].text_content() or "").strip() if len(cells) > 1 else "",
                                    'ip': (cells[2].text_content() or "").strip() if len(cells) > 2 else "",
                                    'comment': (cells[3].text_content() or "").strip() if len(cells) > 3 else ""
                                }
                                # 过滤掉空行
                                if vlan_data['id'] or vlan_data['name']:
                                    vlans.append(vlan_data)
                        break
                except:
                    continue
                    
            self.logger.info(f"获取到过滤后的VLAN列表，共 {len(vlans)} 条记录")
            return vlans
            
        except Exception as e:
            self.logger.error(f"获取过滤后的VLAN列表失败: {e}")
            return []
    
    def clear_search(self):
        """清空搜索框"""
        try:
            self.logger.info("清空搜索框")
            
            # 设置API监听器
            hook_func, matched_calls = self._setup_vlan_api_listener("clear_search")
            self.page.on("requestfinished", hook_func)
            
            try:
                # 严格按照录制代码的三步操作
                self.logger.info("执行清空搜索 - 步骤1: 点击搜索框")
                
                # 步骤1: 点击搜索框
                search_box = self.page.get_by_role("textbox", name="vlanID/Vlan名称/IP/备注")
                if search_box.count() == 0:
                    self.logger.error("未找到搜索框")
                    return False
                    
                search_box.click()
                self.logger.info("✅ 已点击搜索框")
                time.sleep(0.5)
                
                # 步骤2: 清空搜索框
                self.logger.info("执行清空搜索 - 步骤2: 清空搜索框")
                search_box.clear()
                self.logger.info("✅ 已清空搜索框")
                time.sleep(0.5)
                
                # 步骤3: 点击搜索按钮
                self.logger.info("执行清空搜索 - 步骤3: 点击搜索按钮")
                search_buttons = self.page.get_by_role("button")
                if search_buttons.count() > 0:
                    clicked = False
                    for i in range(search_buttons.count()):
                        try:
                            button = search_buttons.nth(i)
                            if button.is_visible():
                                button.click()
                                self.logger.info(f"✅ 已点击搜索按钮 (第{i+1}个按钮)")
                                clicked = True
                                break
                        except Exception as e:
                            self.logger.debug(f"点击第{i+1}个按钮失败: {e}")
                            continue
                    
                    if not clicked:
                        search_box.press("Enter")
                        self.logger.info("✅ 已按回车键执行搜索")
                else:
                    search_box.press("Enter")
                    self.logger.info("✅ 已按回车键执行搜索")
                
                # 等待搜索结果更新
                time.sleep(2)
                self.page.wait_for_load_state("networkidle", timeout=5000)
                self.logger.info("✅ 清空搜索操作完成")
                return True
                        
            finally:
                # 清理API监听器
                self._cleanup_api_listener(hook_func)
                
        except Exception as e:
            self.logger.error(f"清空搜索框失败: {e}")
            return False
    
    def verify_search_results(self, search_term: str, expected_vlans: list):
        """验证搜索结果是否符合预期"""
        try:
            filtered_vlans = self.get_filtered_vlan_list()
            
            # 如果期望的VLAN列表为空，表示应该没有匹配结果
            if not expected_vlans:
                if len(filtered_vlans) == 0:
                    self.logger.info(f"搜索'{search_term}'无匹配结果，符合预期")
                    return True
                else:
                    self.logger.error(f"搜索'{search_term}'应该无匹配结果，但实际找到{len(filtered_vlans)}条")
                    return False
            
            # 验证搜索结果是否包含期望的VLAN
            found_vlan_ids = [vlan['id'] for vlan in filtered_vlans]
            
            # 检查是否所有期望的VLAN都在结果中
            missing_vlans = []
            for expected_id in expected_vlans:
                if expected_id not in found_vlan_ids:
                    missing_vlans.append(expected_id)
            
            # 检查是否有多余的VLAN
            extra_vlans = []
            for found_id in found_vlan_ids:
                if found_id not in expected_vlans:
                    extra_vlans.append(found_id)
            
            if missing_vlans:
                self.logger.error(f"搜索'{search_term}'缺少期望的VLAN: {missing_vlans}")
                return False
                
            if extra_vlans:
                self.logger.error(f"搜索'{search_term}'包含多余的VLAN: {extra_vlans}")
                return False
                
            self.logger.info(f"搜索'{search_term}'结果验证通过，匹配VLAN: {found_vlan_ids}")
            return True
            
        except Exception as e:
            self.logger.error(f"验证搜索结果失败: {e}")
            return False

    def edit_vlan(self, vlan_id: str, edit_data: dict):
        """编辑VLAN配置"""
        try:
            self.logger.info(f"开始编辑VLAN: {vlan_id}")
            
            # 确保在VLAN页面
            if not self.navigate_to_vlan_page():
                return False
            
            # 等待页面加载
            time.sleep(2)
            
            # 步骤1: 点击指定VLAN的编辑按钮
            self.logger.info(f"步骤1: 点击VLAN{vlan_id}的编辑按钮")
            if not self._click_vlan_edit_button(vlan_id):
                return False
            
            # 等待编辑页面加载
            time.sleep(2)
            
            # 步骤2: 测试取消按钮功能
            self.logger.info("步骤2: 测试取消按钮功能")
            # 严格按照录制代码：page.get_by_role("button", name="取消").click()
            try:
                cancel_button = self.page.get_by_role("button", name="取消")
                if cancel_button.count() > 0:
                    cancel_button.click()
                    self.logger.info("✅ 已点击取消按钮")
                    time.sleep(2)
                    
                    # 验证是否返回到列表页面
                    if self.page.url.find("vlan") != -1:
                        self.logger.info("✅ 取消功能正常，已返回VLAN列表页面")
                    else:
                        self.logger.warning("取消后页面状态异常")
                else:
                    self.logger.warning("未找到取消按钮")
            except Exception as e:
                self.logger.warning(f"取消按钮操作失败: {e}")
            
            # 步骤3: 再次点击编辑按钮
            self.logger.info(f"步骤3: 再次点击VLAN{vlan_id}的编辑按钮")
            if not self._click_vlan_edit_button(vlan_id):
                return False
            
            # 等待编辑页面加载
            time.sleep(2)
            
            # 步骤4-10: 执行编辑操作
            if not self._perform_edit_operations(edit_data):
                return False
            
            # 步骤11: 保存修改 - 在保存前设置API监听器
            self.logger.info("步骤11: 保存修改")
            
            # 在点击保存按钮前设置API监听器，只捕获保存操作的API
            hook_func, matched_calls = self._setup_vlan_api_listener(f"edit_save_{vlan_id}")
            
            # 同时监听request和requestfinished事件
            self.page.on("request", hook_func)
            self.page.on("requestfinished", hook_func)
            
            try:
                # 尝试多种保存按钮定位方式
                save_button = None
                save_selectors = [
                    ("button", "保存"),
                    ("button", "确定"),
                    ("button", "提交"),
                    ("link", "保存"),
                    ("link", "确定")
                ]
                
                for role, name in save_selectors:
                    try:
                        button = self.page.get_by_role(role, name=name)
                        if button.count() > 0 and button.first.is_visible():
                            save_button = button.first
                            self.logger.info(f"找到保存按钮: {role}[name='{name}']")
                            break
                    except:
                        continue
                
                if save_button:
                    save_button.click()
                    self.logger.info("✅ 已点击保存按钮")
                    
                    # 等待API调用被捕获
                    self.logger.info("等待API调用捕获...")
                    for i in range(50):  # 等待最多5秒
                        if matched_calls:
                            self.logger.info(f"🎉 检测到API调用 (第{i+1}次检查): {[c['action'] for c in matched_calls]}")
                            break
                        time.sleep(0.1)
                    else:
                        self.logger.warning("⚠️ 等待5秒后仍未检测到API调用")
                    
                    # 等待保存完成
                    time.sleep(2)
                    self.page.wait_for_load_state("networkidle", timeout=10000)
                    
                    self.logger.info("✅ VLAN编辑操作完成")
                    return True
                else:
                    self.logger.error("未找到保存按钮")
                    # 调试：显示页面上所有可见的按钮
                    try:
                        buttons = self.page.get_by_role("button")
                        self.logger.debug(f"页面上的按钮数量: {buttons.count()}")
                        for i in range(min(buttons.count(), 10)):  # 最多显示10个
                            try:
                                button_text = buttons.nth(i).text_content()
                                self.logger.debug(f"按钮{i+1}: '{button_text}'")
                            except:
                                pass
                    except:
                        pass
                    return False
                    
            finally:
                # 清理API监听器
                self._cleanup_api_listener(hook_func)
                
        except Exception as e:
            self.logger.error(f"编辑VLAN失败: {e}")
            self.screenshot.take_screenshot("edit_vlan_error")
            return False
    
    def _click_vlan_edit_button(self, vlan_id: str):
        """点击指定VLAN的编辑按钮"""
        try:
            # 根据录制代码，使用nth(4)定位VLAN888的编辑按钮
            # 但这里我们要更通用，先尝试通过VLAN ID定位
            
            # 方法1: 尝试通过表格行定位
            rows = self.page.query_selector_all("table tbody tr")
            for row in rows:
                cells = row.query_selector_all("td")
                if cells and len(cells) > 0:
                    vlan_id_cell = cells[0].text_content()
                    if vlan_id_cell and vlan_id_cell.strip() == vlan_id:
                        # 找到对应的行，查找编辑按钮
                        edit_buttons = row.query_selector_all("text=编辑")
                        if edit_buttons:
                            edit_buttons[0].click()
                            self.logger.info(f"✅ 已点击VLAN{vlan_id}的编辑按钮")
                            return True
            
            # 方法2: 使用录制代码的方式（作为备用）
            if vlan_id == "888":
                edit_button = self.page.get_by_text("编辑").nth(4)
                if edit_button.count() > 0:
                    edit_button.click()
                    self.logger.info(f"✅ 已点击VLAN{vlan_id}的编辑按钮 (备用方法)")
                    return True
            
            # 方法3: 通用的编辑按钮查找
            edit_buttons = self.page.get_by_text("编辑")
            for i in range(edit_buttons.count()):
                try:
                    # 获取按钮所在行的VLAN ID
                    button = edit_buttons.nth(i)
                    # 这里需要根据实际页面结构调整
                    button.click()
                    self.logger.info(f"✅ 已点击编辑按钮 (通用方法，索引{i})")
                    return True
                except:
                    continue
            
            self.logger.error(f"未找到VLAN{vlan_id}的编辑按钮")
            return False
            
        except Exception as e:
            self.logger.error(f"点击编辑按钮失败: {e}")
            return False
    
    def _perform_edit_operations(self, edit_data: dict):
        """执行编辑操作"""
        try:
            # 步骤4: 修改VLAN名称
            if 'vlan_name' in edit_data:
                self.logger.info("步骤4: 修改VLAN名称")
                # 在编辑页面中查找VLAN名称输入框
                vlan_name_selectors = [
                    "input[name='vlan_name']",
                    "input[name='vlanName']", 
                    "#vlan_name",
                    "#vlanName",
                    "input[placeholder*='vlan名称']",
                    "input[placeholder*='名称']"
                ]
                
                vlan_name_input = None
                for selector in vlan_name_selectors:
                    try:
                        element = self.page.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            vlan_name_input = element.first
                            break
                    except:
                        continue
                
                if vlan_name_input:
                    vlan_name_input.fill(edit_data['vlan_name'])
                    self.logger.info(f"✅ 已修改VLAN名称为: {edit_data['vlan_name']}")
                else:
                    self.logger.warning("未找到VLAN名称输入框")
            
            # 步骤5: 修改IP地址
            if 'ip_addr' in edit_data:
                self.logger.info("步骤5: 修改IP地址")
                # 在编辑页面中查找IP地址输入框，排除搜索框
                ip_selectors = [
                    "input[name='ip_addr']",
                    "input[name='ipAddr']",
                    "input[name='ip']",
                    "#ip_addr",
                    "#ipAddr",
                    "#ip"
                ]
                
                ip_input = None
                for selector in ip_selectors:
                    try:
                        element = self.page.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            # 确保不是搜索框
                            placeholder = element.first.get_attribute("placeholder") or ""
                            if "搜索" not in placeholder and "search" not in placeholder.lower():
                                ip_input = element.first
                                break
                    except:
                        continue
                
                if ip_input:
                    ip_input.fill(edit_data['ip_addr'])
                    self.logger.info(f"✅ 已修改IP地址为: {edit_data['ip_addr']}")
                else:
                    self.logger.warning("未找到IP地址输入框")
            
            # 步骤6: 修改子网掩码 (下拉框选择)
            if 'subnet_mask' in edit_data:
                self.logger.info("步骤6: 修改子网掩码")
                # 根据录制代码：page.get_by_role("combobox").first.select_option("255.255.255.128")
                try:
                    subnet_combobox = self.page.get_by_role("combobox").first
                    if subnet_combobox.count() > 0:
                        subnet_combobox.select_option(edit_data['subnet_mask'])
                        self.logger.info(f"✅ 已修改子网掩码为: {edit_data['subnet_mask']}")
                    else:
                        self.logger.warning("未找到子网掩码下拉框")
                except Exception as e:
                    self.logger.warning(f"修改子网掩码失败: {e}")
            
            # 步骤7: 修改线路配置 (下拉框选择)
            if 'line' in edit_data:
                self.logger.info("步骤7: 修改线路配置")
                # 根据录制代码：page.get_by_role("combobox").nth(1).select_option("lan1")
                try:
                    line_combobox = self.page.get_by_role("combobox").nth(1)
                    if line_combobox.count() > 0:
                        # 先选择vlan201再改回lan1 (根据录制代码)
                        if 'line_temp' in edit_data:
                            line_combobox.select_option(edit_data['line_temp'])
                            time.sleep(0.5)
                        line_combobox.select_option(edit_data['line'])
                        self.logger.info(f"✅ 已修改线路为: {edit_data['line']}")
                    else:
                        self.logger.warning("未找到线路下拉框")
                except Exception as e:
                    self.logger.warning(f"修改线路配置失败: {e}")
            
            # 步骤8: 编辑扩展IP
            if 'extend_ips' in edit_data and edit_data['extend_ips']:
                self.logger.info("步骤8: 编辑扩展IP")
                extend_ip_data = edit_data['extend_ips'][0]
                
                try:
                    # 点击扩展IP的编辑按钮
                    # 根据录制代码：page.get_by_role("rowgroup").get_by_text("编辑").click()
                    extend_edit_button = self.page.get_by_role("rowgroup").get_by_text("编辑")
                    if extend_edit_button.count() > 0:
                        extend_edit_button.click()
                        self.logger.info("✅ 已点击扩展IP编辑按钮")
                        time.sleep(1)
                        
                        # 修改扩展IP的子网掩码
                        # 根据录制代码：page.get_by_role("cell", name="(24)").get_by_role("combobox").select_option("255.255.255.128")
                        try:
                            extend_mask_combobox = self.page.get_by_role("cell", name="(24)").get_by_role("combobox")
                            if extend_mask_combobox.count() > 0:
                                extend_mask_combobox.select_option(extend_ip_data['mask'])
                                self.logger.info(f"✅ 已修改扩展IP子网掩码为: {extend_ip_data['mask']}")
                        except Exception as e:
                            self.logger.warning(f"修改扩展IP子网掩码失败: {e}")
                        
                        # 修改扩展IP地址
                        # 根据录制代码：page.locator("input[name=\"ip\"]").fill("192.168.116.1")
                        # 这里需要区分主IP和扩展IP的输入框
                        try:
                            # 在扩展IP编辑对话框中查找IP输入框
                            extend_ip_input = self.page.locator("input[name=\"ip\"]").last  # 使用last避免选中主IP输入框
                            if extend_ip_input.count() > 0:
                                extend_ip_input.fill(extend_ip_data['ip'])
                                self.logger.info(f"✅ 已修改扩展IP地址为: {extend_ip_data['ip']}")
                        except Exception as e:
                            self.logger.warning(f"修改扩展IP地址失败: {e}")
                        
                        # 确认扩展IP修改
                        # 根据录制代码：page.locator("#fantasyMenu").get_by_text("确定").click()
                        try:
                            confirm_button = self.page.locator("#fantasyMenu").get_by_text("确定")
                            if confirm_button.count() > 0:
                                confirm_button.click()
                                self.logger.info("✅ 已确认扩展IP修改")
                                time.sleep(1)
                        except Exception as e:
                            self.logger.warning(f"确认扩展IP修改失败: {e}")
                    else:
                        self.logger.warning("未找到扩展IP编辑按钮")
                except Exception as e:
                    self.logger.warning(f"编辑扩展IP失败: {e}")
            
            # 步骤9: 修改备注
            if 'comment' in edit_data:
                self.logger.info("步骤9: 修改备注")
                # 在编辑页面中查找备注输入框
                comment_selectors = [
                    "input[name='comment']",
                    "textarea[name='comment']",
                    "#comment",
                    "input[placeholder*='备注']",
                    "textarea[placeholder*='备注']"
                ]
                
                comment_input = None
                for selector in comment_selectors:
                    try:
                        element = self.page.locator(selector)
                        if element.count() > 0 and element.first.is_visible():
                            comment_input = element.first
                            break
                    except:
                        continue
                
                if comment_input:
                    comment_input.fill(edit_data['comment'])
                    self.logger.info(f"✅ 已修改备注为: {edit_data['comment']}")
                else:
                    self.logger.warning("未找到备注输入框")
            
            return True
            
        except Exception as e:
            self.logger.error(f"执行编辑操作失败: {e}")
            return False
    
    def verify_vlan_edited(self, vlan_id: str, expected_data: dict):
        """验证VLAN编辑结果"""
        try:
            self.logger.info(f"验证VLAN{vlan_id}编辑结果")
            
            # 确保在VLAN页面
            if not self.navigate_to_vlan_page():
                return False
            
            # 等待页面加载
            time.sleep(2)
            
            # 获取VLAN列表
            vlans = self.get_vlan_list()
            
            # 调试：显示所有VLAN数据结构
            self.logger.debug(f"当前VLAN列表数据: {vlans}")
            
            # 查找指定的VLAN
            target_vlan = None
            for vlan in vlans:
                if vlan['id'] == vlan_id:
                    target_vlan = vlan
                    break
            
            if not target_vlan:
                self.logger.error(f"未找到VLAN{vlan_id}")
                return False
            
            # 调试：显示目标VLAN的完整数据
            self.logger.info(f"找到目标VLAN数据: {target_vlan}")
            self.logger.info(f"表格结构: vlanID={target_vlan.get('id')}, vlan名称={target_vlan.get('name')}, MAC={target_vlan.get('mac')}, IP={target_vlan.get('ip')}, 子网掩码={target_vlan.get('subnet_mask')}, 线路={target_vlan.get('line')}, 备注={target_vlan.get('comment')}, 状态={target_vlan.get('status')}")
            
            # 验证各字段是否已更新
            verification_results = []
            
            if 'vlan_name' in expected_data:
                if target_vlan['name'] == expected_data['vlan_name']:
                    self.logger.info(f"✅ VLAN名称验证通过: {target_vlan['name']}")
                    verification_results.append(True)
                else:
                    self.logger.error(f"❌ VLAN名称验证失败: 期望{expected_data['vlan_name']}, 实际{target_vlan['name']}")
                    verification_results.append(False)
            
            if 'ip_addr' in expected_data:
                if target_vlan['ip'] == expected_data['ip_addr']:
                    self.logger.info(f"✅ IP地址验证通过: {target_vlan['ip']}")
                    verification_results.append(True)
                else:
                    self.logger.error(f"❌ IP地址验证失败: 期望{expected_data['ip_addr']}, 实际{target_vlan['ip']}")
                    verification_results.append(False)
            
            if 'comment' in expected_data:
                if target_vlan['comment'] == expected_data['comment']:
                    self.logger.info(f"✅ 备注验证通过: {target_vlan['comment']}")
                    verification_results.append(True)
                else:
                    self.logger.error(f"❌ 备注验证失败: 期望{expected_data['comment']}, 实际{target_vlan['comment']}")
                    verification_results.append(False)
            
            # 验证子网掩码（如果有）
            if 'subnet_mask' in expected_data:
                if target_vlan['subnet_mask'] == expected_data['subnet_mask']:
                    self.logger.info(f"✅ 子网掩码验证通过: {target_vlan['subnet_mask']}")
                    verification_results.append(True)
                else:
                    self.logger.error(f"❌ 子网掩码验证失败: 期望{expected_data['subnet_mask']}, 实际{target_vlan['subnet_mask']}")
                    verification_results.append(False)
            
            # 验证线路（如果有）
            if 'line' in expected_data:
                if target_vlan['line'] == expected_data['line']:
                    self.logger.info(f"✅ 线路验证通过: {target_vlan['line']}")
                    verification_results.append(True)
                else:
                    self.logger.error(f"❌ 线路验证失败: 期望{expected_data['line']}, 实际{target_vlan['line']}")
                    verification_results.append(False)
            
            # 总体验证结果
            if all(verification_results):
                self.logger.info(f"✅ VLAN{vlan_id}编辑结果验证通过")
                return True
            else:
                self.logger.error(f"❌ VLAN{vlan_id}编辑结果验证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"验证VLAN编辑结果失败: {e}")
            return False