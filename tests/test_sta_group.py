# 终端分组测试
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


class TestGroup:

    @classmethod
    def setup_class(cls):
        """类级别初始化 - 整个测试类只执行一次"""
        cls.yaml_reader = YamlReader()
        cls.logger = Logger().get_logger()

        try:
            cls.sta_group_ip_data = cls.yaml_reader.read_yaml("data/sta_group.yaml")
            if not cls.sta_group_ip_data:
                raise Exception("终端分组-IP分组测试数据为空")
        except Exception as e:
            cls.logger.error(f"加载终端分组-IP分组数据失败: {str(e)}")
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


    @pytest.fixture(scope="function", autouse=True)
    def setup_page(self, logged_in_page):
        """函数级别fixture - 导航到IP分组页面"""
        self.sta_group_page = StaGroupPage(logged_in_page)

        # 导航到IP分组页面并标记为已加载
        if not self.sta_group_page.navigate_to_ip_group_page():
            pytest.fail("无法导航到IP分组页面")

        self.sta_group_page.mark_ip_group_loaded()
        yield

    @pytest.mark.parametrize("test_case", [
        "基础功能测试（单分组）",
        "批量分组测试",
        "边界值测试",
        "混合格式测试",
        "纯英文分组名称测试",
        "纯数字分组名称测试",
        "中英文混合分组名称测试",
        "英文数字混合分组名称测试"
    ])
    def test_add_valid_ip_groups(self, test_case):
        """测试添加有效的IP分组（不重复导航）"""
        # 获取测试数据
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"] if item["test_case"] == test_case), None)
        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            # 执行添加分组操作
            assert self.sta_group_page.add_group_ip(
                test_data["name"],
                "\n".join(test_data["ip_list"]),
                navigate=False
            )

            # 验证分组
            ip_list_str = "\n".join(test_data["ip_list"])
            assert self.sta_group_page.verify_ip_group_added(test_data["name"], ip_list_str)

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", [
        "特殊字符分组名称测试",
        "中英数特殊字符混合分组名称测试",
        "异常格式测试",
        "超长名称测试",
        "重复IP测试",
        "空分组名称测试",
        "空IP列表测试"
    ])
    def test_add_invalid_ip_groups(self, test_case):
        """测试添加无效的IP分组（连续执行）"""
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"] if item["test_case"] == test_case), None)

        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            actual_name = test_data.get("name", test_case)

            # 检查是否已在添加表单页面
            if not self._is_in_add_form():
                self.sta_group_page.click_text_filter(self.sta_group_page.ip_group_link)
                self.sta_group_page.page.wait_for_selector(
                    f"text={self.sta_group_page.add_link}",
                    state="visible",
                    timeout=5000
                )
                self.sta_group_page.click_link_by_text(self.sta_group_page.add_link)
                self.sta_group_page.page.wait_for_selector(
                    self.sta_group_page.group_name_input,
                    state="visible",
                    timeout=5000
                )

            self._clear_form()
            time.sleep(1)

            ip_list = test_data.get("ip_list", [])

            # 输入分组名称
            self.sta_group_page.input_text(self.sta_group_page.group_name_input, actual_name)

            # 输入IP列表
            ip_text = "\n".join(ip_list) if ip_list else ""
            self.sta_group_page.input_text(self.sta_group_page.group_list_input, ip_text)

            # 点击保存
            self.sta_group_page.click_by_role(*self.sta_group_page.save_button_role)
            time.sleep(1)

            # 验证错误提示信息
            if "expected_error" in test_data:
                actual_error = self.sta_group_page.get_error_tip()
                self.logger.debug(f"实际错误提示: '{actual_error}'")

                if actual_error is None:
                    self.logger.error("未显示任何错误提示")
                    pytest.fail(f"未显示任何错误提示，但预期有: {test_data['expected_error']}")

                # 检查预期错误是否包含在实际错误中
                if test_data["expected_error"] not in actual_error:
                    pytest.fail(f"错误提示不匹配\n预期: {test_data['expected_error']}\n实际: {actual_error}")

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    def _is_in_add_form(self):
        """检查当前是否在添加分组表单页面"""
        return self.sta_group_page.page.query_selector(self.sta_group_page.group_name_input) is not None

    def _clear_form(self):
        """清空表单内容"""
        self.sta_group_page.page.fill(self.sta_group_page.group_name_input, "")
        self.sta_group_page.page.fill(self.sta_group_page.group_list_input, "")

    def teardown_method(self):
        """测试后清理"""
        if hasattr(self, 'test_start_time') and self.test_start_time:
            duration = time.time() - self.test_start_time
            self._log_step(f"测试执行时间: {duration:.2f}秒", "summary")

    @pytest.mark.parametrize("test_case", [
        "搜索测试 - 现有数据",
        "搜索测试 - 没有数据"
    ])
    def test_search_ip_group(self, test_case):
        """测试IP分组搜索功能"""
        # 获取测试数据
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"] if item["test_case"] == test_case), None)
        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            search_name = test_data["name"]
            expected_error = test_data.get("expected_error")

            # 返回到IP列表
            self.sta_group_page.click_text_filter(self.sta_group_page.ip_group_link)

            # 执行搜索操作
            assert self.sta_group_page.search_ip_group(search_name), "搜索操作失败"

            # 验证搜索结果
            if expected_error:
                assert self.sta_group_page.verify_no_data_prompt(), "暂无数据验证失败"
            else:
                assert self.sta_group_page.verify_search_result(search_name, should_exist=True), "分组存在验证失败"

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    # 在TestGroup类中添加以下测试方法
    @pytest.mark.parametrize("test_case", ["编辑分组测试"])
    def test_edit_ip_group(self, test_case):
        """测试编辑IP分组功能"""
        # 获取测试数据
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"]
                          if item["test_case"] == test_case), None)
        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            # 准备数据
            original_name = test_data["original_name"]
            new_name = test_data["new_name"]
            new_ip_str = "\n".join(test_data["new_ip_list"])

            # 执行编辑操作
            assert self.sta_group_page.edit_group_ip(original_name, new_name, new_ip_str)

            # 验证编辑结果
            self.sta_group_page.page.wait_for_selector(
                f"text={self.sta_group_page.add_link}",
                state="visible",
                timeout=5000
            )

            # 搜索并验证新分组
            assert self.sta_group_page.search_ip_group(new_name)
            assert self.sta_group_page.verify_ip_group_added(new_name, new_ip_str)

            # 验证原始分组不存在
            assert self.sta_group_page.search_ip_group(original_name)
            assert self.sta_group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["删除分组测试"])
    def test_delete_ip_group(self, test_case):
        """测试删除IP分组功能"""
        # 获取测试数据
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"]
                          if item["test_case"] == test_case), None)
        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            group_name = test_data["name"]
            # 返回到IP列表
            self.sta_group_page.click_text_filter(self.sta_group_page.ip_group_link)

            # 执行删除操作
            assert self.sta_group_page.delete_group_ip(group_name)

            # 验证删除结果
            assert self.sta_group_page.search_ip_group(group_name)
            assert self.sta_group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise

    @pytest.mark.parametrize("test_case", ["全部删除"])
    def test_delete_all_ip_groups(self, test_case):
        """测试全部删除IP分组功能"""
        test_data = next((item for item in self.sta_group_ip_data["ip_groups"]
                          if item["test_case"] == test_case), None)
        if not test_data:
            pytest.skip(f"未找到测试数据: {test_case}")

        try:
            self.sta_group_page.click_text_filter(self.sta_group_page.ip_group_link)

            # 验证删除结果
            assert self.sta_group_page.delete_all_ip_groups()
            assert self.sta_group_page.verify_no_data_prompt()

            self._log_step(f"测试通过: {test_case}")

        except AssertionError as e:
            self._log_step(f"测试失败: {test_case} - {str(e)}", "error")
            pytest.fail(f"测试失败: {test_case}")
        except Exception as e:
            self._log_step(f"发生异常: {test_case} - {str(e)}", "error")
            raise


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-s",
        "--headed"
    ])