import inspect

import pytest
import sys
import os
from pathlib import Path
import time


# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pages.login_page import LoginPage
from pages.sta_group_page import StaGroupPage
from utils.yaml_reader import YamlReader
from utils.logger import Logger
from utils.screenshot_helper import ScreenshotHelper


class BaseGroupTest:
    """分组测试基类，包含公共方法"""
    @classmethod
    def setup_class(cls):
        """类级别初始化 - 整个测试类只执行一次"""
        cls.yaml_reader = YamlReader()
        cls.logger = Logger().get_logger()
        cls.sta_group_page = None

        try:
            cls.sta_group_data = cls.yaml_reader.read_yaml("data/sta_group.yaml")
            if not cls.sta_group_data:
                raise Exception("终端分组测试数据为空")
        except Exception as e:
            cls.logger.error(f"加载终端分组数据失败: {str(e)}")
            pytest.fail(f"无法加载测试数据: {str(e)}")

        # 存储执行详情
        cls.execution_details = []

    def _log_step(self, step_info, step_type="step"):
        """记录测试步骤日志"""
        timestamp = time.strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {step_info}"
        self.logger.info(log_message)

    def setup_method(self):
        """测试方法级别初始化"""
        self.test_start_time = time.time()
        self.logger.info("")
        self.logger.info(("=" * 80))
        self._log_step(f"开始测试: {self.__class__.__name__}")

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'test_start_time') and self.test_start_time:
            duration = time.time() - self.test_start_time
            self._log_step(f"测试执行时间: {duration:.2f}秒", "summary")

    def _refresh_page(self):
        """通用页面刷新函数"""
        try:
            self.logger.info("刷新页面以恢复状态...")
            self.sta_group_page.page.reload()
            self.sta_group_page.page.wait_for_load_state("networkidle")
            time.sleep(2)
            self.logger.info("页面刷新完成")
        except Exception as e:
            self.logger.error(f"页面刷新失败: {str(e)}")

class GroupTestBase(BaseGroupTest):
    """分组测试基类，包含所有测试方法"""
    group_type = None  # 子类需要覆盖这个属性

    @pytest.fixture(scope="function", autouse=True)
    def setup_page(self, logged_in_page):
        """动态设置分组类型"""
        if self.group_type is None:
            pytest.fail("group_type 未设置，请在子类中指定")

        self.sta_group_page = StaGroupPage(logged_in_page)
        self.group_page = getattr(self.sta_group_page, f"{self.group_type}_group")

        # 导航到对应分组页面
        navigate_method = getattr(self.group_page, f"navigate_to_{self.group_type}_group_page")
        if not navigate_method():
            pytest.fail(f"无法导航到{self.group_type.upper()}分组页面")
        yield

    @pytest.mark.parametrize("test_case", [
        "基础功能测试（单分组）",
        "批量分组测试",
        "边界值测试",
        "混合格式测试",
        "纯英文分组名称测试",
        "纯数字分组名称测试",
        "中英文混合分组名称测试",
        "英文数字混合分组名称测试",
        "备注测试",
        "混合备注测试",
        "特殊字符备注测试"
    ])
    def test_add_valid_groups(self, test_case):
        """测试添加有效的分组"""
        # 获取测试数据
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:

            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)
            time.sleep(1)

            # 执行添加分组操作
            assert self.group_page.add_group(
                test_data["name"],
                "\n".join(test_data["addr_list"]),
                navigate=False
            )

            # 验证分组
            addr_list_str = "\n".join(test_data["addr_list"])
            assert self.group_page.verify_group_added(test_data["name"], addr_list_str)

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", [
        "特殊字符分组名称测试",
        "中英数特殊字符混合分组名称测试",
        "异常格式测试",
        "超长名称测试",
        "重复测试",
        "空分组名称测试",
        "空列表测试",
        "超长地址测试"
    ])
    def test_add_invalid_groups(self, test_case):
        """测试添加无效的分组"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            actual_name = test_data.get("name", test_case)

            # 确保在分组列表页面（回退操作）
            group_link = self.group_page.group_link
            if not self.sta_group_page.click_text_filter(group_link):
                pytest.fail(f"无法返回到{self.group_type.upper()}分组列表页面")
            time.sleep(1)

            # 点击添加按钮
            self.sta_group_page.click_link_by_text(self.group_page.add_link)
            self.sta_group_page.page.wait_for_selector(
                self.group_page.group_name_input,
                state="visible",
                timeout=5000
            )

            addr_list = test_data.get("addr_list", [])

            # 输入分组名称
            self.sta_group_page.input_text(self.group_page.group_name_input, actual_name)

            # 输入地址列表
            addr_text = "\n".join(addr_list) if addr_list else ""
            self.sta_group_page.input_text(self.group_page.group_list_input, addr_text)

            # 点击保存
            self.sta_group_page.click_by_role(*self.group_page.save_button_role)
            time.sleep(1)

            # 验证错误提示信息
            if "expected_error" in test_data:
                actual_error = self.group_page.get_error_tip()
                self.logger.debug(f"实际错误提示: '{actual_error}'")

                if actual_error is None:
                    self.logger.error("未显示任何错误提示")
                    pytest.fail(f"未显示任何错误提示，但预期有: {test_data['expected_error']}")

                # 检查预期错误是否包含在实际错误中
                if test_data["expected_error"] not in actual_error:
                    pytest.fail(f"错误提示不匹配\n预期: {test_data['expected_error']}\n实际: {actual_error}")

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["重复分组名称测试"])
    def test_duplicate_group_name(self, test_case):
        """测试添加重复分组名称"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)

            group_name = test_data["name"]
            addr_list = test_data["addr_list"]
            addr_str = "\n".join(addr_list)
            expected_error = test_data.get("expected_errors", [])

            # 先添加一个正常分组
            assert self.group_page.add_group(
                group_name,
                addr_str,
                navigate=True
            ), "首次添加分组失败"

            # 尝试再次添加相同名称的分组
            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)
            time.sleep(1)

            self.sta_group_page.click_link_by_text(self.group_page.add_link)
            self.sta_group_page.page.wait_for_selector(
                self.group_page.group_name_input,
                state="visible",
                timeout=5000
            )

            self.sta_group_page.input_text(self.group_page.group_name_input, group_name)
            self.sta_group_page.input_text(self.group_page.group_list_input, addr_str)
            self.sta_group_page.click_by_role(*self.group_page.save_button_role)
            time.sleep(1)

            # 验证错误提示
            actual_error = self.group_page.get_duplicate_error()
            self.logger.debug(f"实际错误提示: '{actual_error}'")

            if not actual_error:
                pytest.fail("未显示任何错误提示")

            # 验证错误内容是否符合预期
            assert any(exp in actual_error for exp in expected_error), \
                f"错误提示不匹配\n预期之一: {expected_error}\n实际: {actual_error}"

            # 关闭错误提示
            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", [
        "搜索测试 - 现有数据",
        "搜索测试 - 没有数据"
    ])
    def test_search_group(self, test_case):
        """测试分组搜索功能"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            search_name = test_data["name"]
            expected_error = test_data.get("expected_error")

            # 返回到列表
            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)

            # 执行搜索操作
            assert self.group_page.search_group(search_name), "搜索操作失败"

            # 验证搜索结果
            if expected_error:
                assert self.group_page.verify_no_data_prompt(), "暂无数据验证失败"
            else:
                assert self.group_page.verify_search_result(search_name, should_exist=True), "分组存在验证失败"

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["编辑分组测试"])
    def test_edit_group(self, test_case):
        """测试编辑分组功能"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            # 准备数据
            original_name = test_data["original_name"]
            new_name = test_data["new_name"]
            new_addr_str = "\n".join(test_data["new_addr_list"])

            # 执行编辑操作
            assert self.group_page.edit_group(original_name, new_name, new_addr_str)

            # 验证编辑结果
            self.sta_group_page.page.wait_for_selector(
                f"text={self.group_page.add_link}",
                state="visible",
                timeout=5000
            )

            # 搜索并验证新分组
            assert self.group_page.search_group(new_name)
            assert self.group_page.verify_group_added(new_name, new_addr_str)

            # 验证原始分组不存在
            assert self.group_page.search_group(original_name)
            assert self.group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["删除分组测试"])
    def test_delete_group(self, test_case):
        """测试删除分组功能"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            group_name = test_data["name"]
            # 返回到列表
            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)

            # 执行删除操作
            assert self.group_page.delete_group(group_name)

            # 验证删除结果
            assert self.group_page.search_group(group_name)
            assert self.group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["全部删除"])
    def test_delete_all_groups(self, test_case):
        """测试全部删除分组功能"""
        group_data = self.sta_group_data["groups"]
        test_data = next((item for item in group_data
                          if item["test_case"] == test_case and item["type"] == self.group_type), None)
        if not test_data:
            pytest.skip(f"未找到{self.group_type.upper()}分组的测试数据: {test_case}")

        try:
            group_link = self.group_page.group_link
            self.sta_group_page.click_text_filter(group_link)

            # 验证删除结果
            assert self.group_page.delete_all_groups()
            assert self.group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._refresh_page()
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._refresh_page()
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise


class TestIPGroup(GroupTestBase):
    group_type = "ip"

class TestIPv6Group(GroupTestBase):
    group_type = "ipv6"

class TestMACGroup(GroupTestBase):
    group_type = "mac"

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-s",
        "--headed"
    ])