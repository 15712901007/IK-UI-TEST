# 终端分组类
from pages.base_page import BasePage
from playwright.sync_api import Page
import time
from utils.constants import DOWNLOAD_DIR
from pathlib import Path
import json


class StaGroupPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self._is_ip_group_page_loaded = False

        # 导航菜单
        self.network_settings_text = "网络设置"
        self.sta_group_setting = "终端分组设置"
        self.ip_group_link = 'IP分组'

        # 操作按钮
        self.add_link = '添加'
        self.delete_link = '删除'
        self.save_button_role = ("button", "保存")
        self.confirm_button_role = ("button", "确定")

        # IP分组表单
        self.group_name_input = "input[name='group_name']"
        self.group_list_input = "textarea[name='addr_pool']"

        # 错误提示选择器
        self.error_tip_selector = "p.error_tip"

        # 搜索
        self.search = "input[name='searchText']"
        self.search_button = "input.search_icon"

        # 删除复选框
        self.select_all_checkbox = "label.checkbox.input_opera"

    # 导航到IP分组
    def navigate_to_ip_group_page(self) -> bool:
        """ 导航到IP分组设置页面 """
        if self.page.url and "/ip-group" in self.page.url:
            self.logger.info("已在IP分组页面，跳过导航")
            self._is_ip_group_page_loaded = True
            return True

        try:
            self.logger.info("开始导航到IP分组页面")

            # 点击网络设置主菜单
            if not self.click_text_filter(self.network_settings_text):
                raise Exception("网络设置菜单未找到")

            self.page.wait_for_selector(
                f"text={self.sta_group_setting}",
                state="visible",
                timeout=5000
            )

            # 点击终端分组设置子菜单
            if not self.click_text_filter(self.sta_group_setting):
                raise Exception("终端分组设置菜单未找到")

            self.page.wait_for_selector(
                f"text={self.ip_group_link}",
                state="attached",
                timeout=3000
            )

            # 点击IP分组
            if not self.click_text_filter(self.ip_group_link):
                raise Exception("IP分组未找到")

            self.page.wait_for_url("**/ip-group*", timeout=10000)
            self.page.wait_for_load_state("networkidle")

            self._is_ip_group_page_loaded = True
            self.logger.info("成功导航到IP分组页面")
            return True

        except Exception as e:
            self.logger.error(f"导航到IP分组页面失败: {str(e)}", exc_info=True)
            self.screenshot.take_screenshot("ip_group_navigation_error")
            return False

    def mark_ip_group_loaded(self):
        """标记IP分组页面已加载"""
        self._is_ip_group_page_loaded = True

    def add_group_ip(self, name: str, ip_list: str, navigate: bool = True) -> bool:
        """添加IP分组"""
        try:
            self.logger.info(f"添加分组: {name}, IP: {ip_list}")

            # 1. 导航到页面（可选）
            if navigate:
                if not self.navigate_to_ip_group_page():
                    self.logger.error("导航到IP分组页面失败")
                    return False
            elif not self._is_ip_group_page_loaded:
                self.logger.warning("跳过导航但页面未标记为已加载")

            # 2. 点击添加按钮
            if not self.click_link_by_text(self.add_link):
                self.logger.error("添加按钮点击失败")
                return False
            time.sleep(1)

            # 3. 输入分组名称
            if not self.input_text(self.group_name_input, name):
                self.logger.error("分组名称输入失败")
                return False

            # 4. 输入IP列表
            if not self.input_text(self.group_list_input, ip_list):
                self.logger.error("IP列表输入失败")
                return False

            # 5. 点击保存
            if not self.click_by_role(*self.save_button_role):
                self.logger.error("保存按钮点击失败")
                return False

            # 6. 添加成功时显式返回True
            self.logger.info("IP分组添加成功")
            return True

        except Exception as e:
            self.logger.error(f"添加分组异常: {str(e)}")
            return False

    def verify_ip_group_added(self, group_name: str, expected_ips: str) -> bool:
        """
        P分组验证函数
        参数:
            group_name: 要验证的分组名称
            expected_ips: 期望的IP列表（换行符分隔的字符串）
        """
        try:
            self.logger.info(f"开始验证分组: {group_name}")

            # 1. 等待页面刷新完成
            self.page.wait_for_load_state("networkidle")
            time.sleep(1)  # 额外等待1秒确保完全加载

            # 2. 改进分组行定位方式（尝试多种选择器）
            group_row = None
            selectors = [
                f"tr:has(td:has-text('{group_name}'))",  # 首选选择器
                f"//tr[.//*[contains(text(), '{group_name}')]]",  # XPath备用
                f"tr:has(span:text-is('{group_name}'))"  # 另一种可能的结构
            ]

            for selector in selectors:
                if self.page.query_selector(selector):
                    group_row = self.page.query_selector(selector)
                    break

            if not group_row:
                # 尝试更宽松的匹配方式
                group_row = self.page.query_selector(f"tr:has(td:text-matches('{group_name}'))")
                if not group_row:
                    self.logger.error(f"未找到分组行: {group_name}")
                    self.screenshot.take_screenshot(f"verify_group_{group_name}_failed")
                    return False

            # 3. 获取实际IP列表（更健壮的处理方式）
            ip_cell = group_row.query_selector("td:nth-child(2), td.td-IPwrap2, td.ip-cell")
            if not ip_cell:
                self.logger.error("找不到IP列表单元格")
                return False

            actual_ips = ip_cell.inner_text().replace("\u00A0", " ").replace("\n", " ").strip()
            self.logger.debug(f"实际IP内容: {actual_ips}")

            # 4. 验证每个期望的IP
            for ip in [x.strip() for x in expected_ips.split('\n') if x.strip()]:
                if ip not in actual_ips:
                    self.logger.error(f"IP验证失败: 期望 '{ip}' 不在实际IP列表 '{actual_ips}' 中")
                    return False

            self.logger.info(f"分组 '{group_name}' 验证成功")
            return True

        except Exception as e:
            self.logger.error(f"验证过程中发生异常: {str(e)}", exc_info=True)
            self.screenshot.take_screenshot(f"verify_group_exception_{group_name}")
            return False

    def get_error_tip(self):
        """获取错误提示文本"""
        try:
            # 等待错误提示元素出现 - 增加超时时间
            self.page.wait_for_selector(
                self.error_tip_selector,
                state="visible",
                timeout=5000  # 增加超时时间确保加载
            )

            # 获取所有错误提示元素
            error_elements = self.page.query_selector_all(self.error_tip_selector)

            # 收集所有可见的错误提示文本
            visible_errors = []
            for element in error_elements:
                if element.is_visible():
                    error_text = element.inner_text().strip()
                    if error_text:
                        visible_errors.append(error_text)

            # 合并所有错误提示
            if visible_errors:
                return "\n".join(visible_errors)

        except:
            pass

        # 尝试另一种可能的错误提示位置（全局提示）
        try:
            toast_error = self.page.query_selector(".toast-error, .global-error")
            if toast_error and toast_error.is_visible():
                return toast_error.inner_text().strip()
        except:
            pass

        # 尝试输入框下方的错误提示（特定位置）
        try:
            input_error = self.page.query_selector(".input_P > .error_tip")
            if input_error and input_error.is_visible():
                return input_error.inner_text().strip()
        except:
            pass

        return None

    def search_ip_group(self, name: str) -> bool:
        """执行搜索操作"""
        try:
            self.logger.info(f"搜索分组: {name}")

            # 确保在分组列表页面
            if not self.navigate_to_ip_group_page():
                self.logger.error("无法导航到IP分组页面")
                return False

            # 输入搜索词
            self.input_text(self.search, name)

            # 点击搜索按钮
            self.page.click(self.search_button)
            time.sleep(1)

            self.logger.info("搜索操作完成")
            return True
        except Exception as e:
            self.logger.error(f"搜索分组异常: {str(e)}")
            return False

    def verify_search_result(self, name: str, should_exist: bool) -> bool:
        """ 验证搜索结果 """
        try:
            self.logger.info(f"验证搜索结果: 分组'{name}'应{'存在' if should_exist else '不存在'}")

            # 验证分组是否存在
            selector = f"tr:has(td:has-text('{name}'))"
            group_row = self.page.query_selector(selector)

            if should_exist:
                if not group_row or not group_row.is_visible():
                    self.logger.error(f"未找到分组: {name}")
                    return False
            else:
                if group_row and group_row.is_visible():
                    self.logger.error(f"分组'{name}'不应该存在但被找到")
                    return False

            self.logger.info("搜索结果验证成功")
            return True
        except Exception as e:
            self.logger.error(f"验证搜索结果异常: {str(e)}")
            return False

    def verify_no_data_prompt(self) -> bool:
        """验证显示'暂无数据'提示"""
        try:
            self.logger.info("验证暂无数据提示")
            no_data_selector = "span.remark:text('暂无数据')"
            no_data_element = self.page.query_selector(no_data_selector)

            if not no_data_element or not no_data_element.is_visible():
                self.logger.error("未显示'暂无数据'提示")
                return False

            actual_text = no_data_element.inner_text().strip()
            if actual_text != "暂无数据":
                self.logger.error(f"提示文本不匹配, 预期: '暂无数据', 实际: '{actual_text}'")
                return False

            self.logger.info("成功显示'暂无数据'提示")
            return True
        except Exception as e:
            self.logger.error(f"验证暂无数据异常: {str(e)}")
            return False

    # 在StaGroupPage类中添加以下方法
    def edit_group_ip(self, original_name: str, new_name: str, new_ip_list: str) -> bool:
        """编辑IP分组"""
        try:
            self.logger.info(f"开始编辑分组: {original_name} -> {new_name}")

            # 1. 确保在分组列表页面
            if not self.navigate_to_ip_group_page():
                self.logger.error("无法导航到IP分组页面")
                return False

            # 2. 搜索要编辑的分组
            self.search_ip_group(original_name)
            time.sleep(1)

            # 3. 定位分组行
            group_row = self.page.query_selector(f"tr:has(td:has-text('{original_name}'))")
            if not group_row:
                self.logger.error(f"未找到分组: {original_name}")
                return False

            # 4. 点击编辑按钮
            edit_btn = group_row.query_selector("a:has-text('编辑')")
            if not edit_btn:
                self.logger.error("未找到编辑按钮")
                return False

            edit_btn.click()
            time.sleep(1)

            # 5. 修改分组信息
            # 清空原有内容
            self.page.fill(self.group_name_input, "")
            self.page.fill(self.group_list_input, "")

            # 输入新名称
            self.page.fill(self.group_name_input, new_name)

            # 输入新IP列表
            self.page.fill(self.group_list_input, new_ip_list)

            # 6. 点击保存
            self.click_by_role(*self.save_button_role)
            time.sleep(1)

            self.logger.info("保存后点击IP分组链接刷新列表")
            if not self.click_text_filter(self.ip_group_link):
                self.logger.error("无法点击IP分组链接")
                return False
            time.sleep(1)

            self.logger.info("分组编辑成功")
            return True

        except Exception as e:
            self.logger.error(f"编辑分组异常: {str(e)}")
            return False

    def delete_group_ip(self, name: str) -> bool:
        """删除指定名称的IP分组"""
        try:
            self.logger.info(f"开始删除分组: {name}")

            # 确保在分组列表页面
            if not self.navigate_to_ip_group_page():
                self.logger.error("无法导航到IP分组页面")
                return False

            # 搜索分组
            self.search_ip_group(name)
            time.sleep(1)

            # 定位分组行
            group_row = self.page.query_selector(f"tr:has(td:has-text('{name}'))")
            if not group_row:
                self.logger.error(f"未找到分组: {name}")
                return False

            # 点击删除按钮
            delete_btn = group_row.query_selector("a:has-text('删除')")
            if not delete_btn:
                self.logger.error("未找到删除按钮")
                return False

            delete_btn.click()
            time.sleep(1)

            # 点击确认按钮
            if not self.click_by_role(*self.confirm_button_role):
                self.logger.error("确认按钮点击失败")
                return False

            # 等待删除完成
            time.sleep(2)
            self.logger.info("分组删除成功")
            return True

        except Exception as e:
            self.logger.error(f"删除分组异常: {str(e)}")
            return False

    def delete_all_ip_groups(self) -> bool:
        """删除所有IP分组"""
        try:
            self.logger.info("开始执行全部删除操作")

            # 点击全选复选框
            if not self.page.is_visible(self.select_all_checkbox):
                self.logger.error("全选复选框未找到")
                return False

            self.click_element(self.select_all_checkbox)
            time.sleep(1)

            # 点击批量删除按钮
            if not self.click_link_by_text(self.delete_link):
                self.logger.error("删除按钮未找到")
                return False

            # 点击确认按钮
            if not self.click_by_role(*self.confirm_button_role):
                self.logger.error("确认按钮点击失败")
                return False

            # 等待删除完成
            time.sleep(2)
            self.logger.info("全部分组删除成功")
            return True

        except Exception as e:
            self.logger.error(f"全部删除过程中发生异常: {str(e)}")
            return False