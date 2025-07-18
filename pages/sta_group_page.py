import re

from pages.base_page import BasePage
from playwright.sync_api import Page
import time
from pathlib import Path
import json


def normalize_mac(mac_str):
    """将MAC地址转换为统一格式"""
    clean_mac = ''.join(filter(str.isalnum, mac_str)).upper()
    return ':'.join(clean_mac[i:i + 2] for i in range(0, 12, 2))

class StaGroupPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)

        # 导航菜单
        self.network_settings_text = "网络设置"
        self.sta_group_setting = "终端分组设置"
        self.ip_group_link = 'IP分组'
        self.mac_group_link = 'MAC分组'
        self.ipv6_group_link = 'IPv6分组'

    def navigate_to_sta_group_setting(self) -> bool:
        """导航到终端分组设置主页面"""
        try:
            if self.page.is_visible(f"text={self.ip_group_link}") or \
                    self.page.is_visible(f"text={self.mac_group_link}"):
                self.logger.debug("二级菜单已展开，无需再次点击")
                return True

            if not self.page.is_visible(f"text={self.network_settings_text} + ul"):
                self.logger.debug("展开主菜单")
                if not self.click_text_filter(self.network_settings_text):
                    return False

            self.logger.debug("展开二级菜单")
            if not self.click_text_filter(self.sta_group_setting):
                return False

            self.page.wait_for_selector(f"text={self.ip_group_link}", state="visible", timeout=5000)
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"导航到终端分组设置失败: {str(e)}")
            return False

    @property
    def ip_group(self):
        """访问IP分组模块"""
        return BaseGroup(self.page, "ip")

    @property
    def mac_group(self):
        """访问MAC分组模块"""
        return BaseGroup(self.page, "mac")

    @property
    def ipv6_group(self):
        """访问IPv6分组模块"""
        return BaseGroup(self.page, "ipv6")


class BaseGroup(BasePage):
    """分组基础功能模块"""

    def __init__(self, page: Page, group_type: str):
        super().__init__(page)
        self.group_type = group_type
        self.group_link = f"{group_type.upper()}分组"
        self._is_group_page_loaded = False

        # 操作按钮
        self.add_link = '添加'
        self.delete_link = '删除'
        self.save_button_role = ("button", "保存")
        self.confirm_button_role = ("button", "确定")

        # 分组表单
        self.group_name_input = "input[name='group_name']"
        self.group_list_input = "textarea[name='addr_pool']"

        # 错误提示选择器
        self.error_tip_selector = "p.error_tip"

        # 搜索
        self.search = "input[name='searchText']"
        self.search_button = "input.search_icon"

        # 删除复选框
        self.select_all_checkbox = "label.checkbox.input_opera"

    def navigate_to_ip_group_page(self):
        return self.navigate_to_group_page()

    def navigate_to_mac_group_page(self):
        return self.navigate_to_group_page()

    def navigate_to_ipv6_group_page(self):
        return self.navigate_to_group_page()


    def navigate_to_group_page(self) -> bool:
        """通用导航方法"""
        if self.page.url and f"/{self.group_type}-group" in self.page.url:
            self._is_group_page_loaded = True
            return True

        try:
            if not StaGroupPage(self.page).navigate_to_sta_group_setting():
                return False

            if not self.click_text_filter(self.group_link):
                return False

            self.page.wait_for_url(f"**/{self.group_type}-group*", timeout=10000)
            self._is_group_page_loaded = True
            return True
        except Exception as e:
            self.logger.error(f"导航到{self.group_type.upper()}分组页面失败: {str(e)}")
            return False

    def add_group(self, name: str, addr_list: str, navigate: bool = True) -> bool:
        """通用添加分组"""
        try:
            self.logger.info(f"添加{self.group_type.upper()}分组: {name}")

            # 导航到页面（可选）
            if navigate:
                if not self.navigate_to_group_page():
                    self.logger.error(f"导航到{self.group_type.upper()}分组页面失败")
                    return False
            elif not self._is_group_page_loaded:
                self.logger.warning("跳过导航但页面未标记为已加载")

            # 点击添加按钮
            if not self.click_link_by_text(self.add_link):
                self.logger.error("添加按钮点击失败")
                return False
            time.sleep(1)

            # 输入分组名称
            if not self.input_text(self.group_name_input, name):
                self.logger.error("分组名称输入失败")
                return False

            # 输入地址列表
            if not self.input_text(self.group_list_input, addr_list):
                self.logger.error(f"{self.group_type.upper()}列表输入失败")
                return False

            # 点击保存
            if not self.click_by_role(*self.save_button_role):
                self.logger.error("保存按钮点击失败")
                return False

            return True

        except Exception as e:
            self.logger.error(f"添加{self.group_type.upper()}分组异常: {str(e)}")
            return False

    def verify_group_added(self, group_name: str, expected_addrs: str) -> bool:
        """通用分组验证，忽略备注信息"""
        try:
            self.logger.info(f"开始验证分组: {group_name}")

            # 等待页面刷新完成
            self.page.wait_for_load_state("networkidle")
            time.sleep(1)

            # 分组行定位
            group_row = self.page.query_selector(f"tr:has(td:has-text('{group_name}'))")
            if not group_row:
                group_row = self.page.query_selector(f"tr:has(td:text-matches('{group_name}'))")
                if not group_row:
                    self.logger.error(f"未找到分组行: {group_name}")
                    return False

            # 获取实际地址列表
            addr_cell = group_row.query_selector("td:nth-child(2)")
            if not addr_cell:
                self.logger.error("找不到地址列表单元格")
                return False

            actual_addrs_text = addr_cell.inner_text().replace("\u00A0", " ").strip()
            self.logger.debug(f"实际地址内容: {actual_addrs_text}")

            def extract_pure_addresses(text):
                """从文本中提取纯地址部分，忽略备注"""
                pure_addresses = []
                for line in text.split('\n'):
                    if line.strip():
                        parts = line.strip().split(maxsplit=1)
                        pure_addresses.append(parts[0])
                return pure_addresses

            # 处理期望地址（同样忽略备注）
            expected_pure_addrs = extract_pure_addresses(expected_addrs)
            actual_pure_addrs = extract_pure_addresses(actual_addrs_text)

            self.logger.debug(f"提取后的期望地址: {expected_pure_addrs}")
            self.logger.debug(f"提取后的实际地址: {actual_pure_addrs}")

            # 特殊处理MAC地址
            if self.group_type == "mac":
                # 将期望和实际的MAC地址都标准化
                normalized_expected = [normalize_mac(mac) for mac in expected_pure_addrs]
                normalized_actual = [normalize_mac(mac) for mac in actual_pure_addrs]

                # 验证每个期望的MAC
                for exp_mac in normalized_expected:
                    if exp_mac not in normalized_actual:
                        self.logger.error(f"MAC验证失败: 期望 '{exp_mac}' 不在实际MAC列表")
                        return False

                # 同时验证实际地址中没有额外的MAC
                for act_mac in normalized_actual:
                    if act_mac not in normalized_expected:
                        self.logger.error(f"MAC验证失败: 实际 '{act_mac}' 不在期望列表中")
                        return False
            elif self.group_type == "ipv6":
                # 标准化IPv6地址（小写、去除多余空格）
                normalized_expected = [addr.strip().lower() for addr in expected_pure_addrs]
                normalized_actual = [addr.strip().lower() for addr in actual_pure_addrs]

                # 验证每个期望的IPv6地址
                for exp_ipv6 in normalized_expected:
                    if exp_ipv6 not in normalized_actual:
                        self.logger.error(f"IPv6验证失败: 期望 '{exp_ipv6}' 不在实际IPv6列表")
                        return False

                # 验证实际地址中没有额外的IPv6地址
                for act_ipv6 in normalized_actual:
                    if act_ipv6 not in normalized_expected:
                        self.logger.error(f"IPv6验证失败: 实际 '{act_ipv6}' 不在期望列表中")
                        return False

            else:
                # 对于IP分组，验证每个期望IP
                for ip in expected_pure_addrs:
                    if ip not in actual_pure_addrs:
                        self.logger.error(f"IP验证失败: 期望 '{ip}' 不在实际IP列表")
                        return False

                # 同时验证实际地址中没有额外的IP
                for ip in actual_pure_addrs:
                    if ip not in expected_pure_addrs:
                        self.logger.error(f"IP验证失败: 实际 '{ip}' 不在期望列表中")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"验证过程中发生异常: {str(e)}")
            return False

    def get_duplicate_error(self):
        """获取重复名称的错误提示文本"""
        try:
            # 等待错误提示弹窗出现
            self.page.wait_for_selector("div.el-message__group", state="visible", timeout=5000)

            # 获取错误文本
            error_element = self.page.query_selector("div.el-message__group p")
            if error_element and error_element.is_visible():
                return error_element.inner_text().strip()
            return None
        except:
            return None

    def get_error_tip(self):
        """获取错误提示文本"""
        try:
            self.page.wait_for_selector(
                self.error_tip_selector,
                state="visible",
                timeout=5000
            )
            error_elements = self.page.query_selector_all(self.error_tip_selector)
            visible_errors = [element.inner_text().strip() for element in error_elements if element.is_visible()]
            return "\n".join(visible_errors) if visible_errors else None
        except:
            return None

    def search_group(self, name: str) -> bool:
        """执行搜索操作"""
        try:
            if not self.navigate_to_group_page():
                self.logger.error(f"无法导航到{self.group_type.upper()}分组页面")
                return False

            self.input_text(self.search, name)
            self.page.click(self.search_button)
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.error(f"搜索分组异常: {str(e)}")
            return False

    def verify_search_result(self, name: str, should_exist: bool) -> bool:
        """验证搜索结果"""
        try:
            selector = f"tr:has(td:has-text('{name}'))"
            group_row = self.page.query_selector(selector)

            if should_exist:
                return group_row and group_row.is_visible()
            else:
                return not (group_row and group_row.is_visible())
        except Exception as e:
            self.logger.error(f"验证搜索结果异常: {str(e)}")
            return False

    def verify_no_data_prompt(self) -> bool:
        """验证显示'暂无数据'提示"""
        try:
            no_data_selector = "span.remark:text('暂无数据')"
            no_data_element = self.page.query_selector(no_data_selector)
            return no_data_element and no_data_element.is_visible() and no_data_element.inner_text().strip() == "暂无数据"
        except:
            return False

    def edit_group(self, original_name: str, new_name: str, new_addr_list: str) -> bool:
        """编辑分组"""
        try:
            if not self.navigate_to_group_page():
                self.logger.error(f"无法导航到{self.group_type.upper()}分组页面")
                return False

            self.search_group(original_name)
            time.sleep(1)

            group_row = self.page.query_selector(f"tr:has(td:has-text('{original_name}'))")
            if not group_row:
                return False

            edit_btn = group_row.query_selector("a:has-text('编辑')")
            if not edit_btn:
                return False
            edit_btn.click()
            time.sleep(1)

            self.page.fill(self.group_name_input, "")
            self.page.fill(self.group_list_input, "")
            self.page.fill(self.group_name_input, new_name)
            self.page.fill(self.group_list_input, new_addr_list)

            self.click_by_role(*self.save_button_role)
            time.sleep(1)

            if not self.click_text_filter(self.group_link):
                return False
            time.sleep(1)
            return True

        except Exception as e:
            self.logger.error(f"编辑分组异常: {str(e)}")
            return False

    def delete_group(self, name: str) -> bool:
        """删除指定名称的分组"""
        try:
            if not self.navigate_to_group_page():
                self.logger.error(f"无法导航到{self.group_type.upper()}分组页面")
                return False

            self.search_group(name)
            time.sleep(1)

            group_row = self.page.query_selector(f"tr:has(td:has-text('{name}'))")
            if not group_row:
                return False

            delete_btn = group_row.query_selector("a:has-text('删除')")
            if not delete_btn:
                return False
            delete_btn.click()
            time.sleep(1)

            if not self.click_by_role(*self.confirm_button_role):
                return False
            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"删除分组异常: {str(e)}")
            return False

    def delete_all_groups(self) -> bool:
        """删除所有分组"""
        try:
            if not self.page.is_visible(self.select_all_checkbox):
                return False

            self.click_element(self.select_all_checkbox)
            time.sleep(1)

            if not self.click_link_by_text(self.delete_link):
                return False

            if not self.click_by_role(*self.confirm_button_role):
                return False
            time.sleep(2)
            return True

        except Exception as e:
            self.logger.error(f"全部删除过程中发生异常: {str(e)}")
            return False