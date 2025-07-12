# 登录功能测试
import pytest
import sys
import os
from pathlib import Path
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pages.login_page import LoginPage
from utils.yaml_reader import YamlReader
from utils.logger import Logger

class TestLogin:
    """登录功能测试类 - 优化版（统一日志格式）"""
    
    def setup_method(self):
        """测试前准备"""
        self.yaml_reader = YamlReader()
        self.logger = Logger().get_logger()
        self.config = self.yaml_reader.read_yaml("config/test_config.yaml")
        self.test_start_time = None
        self.execution_details = []
        
    def _log_step(self, step_info, step_type="step"):
        """统一记录步骤，方便报告解析"""
        timestamp = time.strftime('%H:%M:%S')
        self.execution_details.append({
            'timestamp': timestamp,
            'step': step_info,
            'type': step_type
        })
        self.logger.info(f"[执行步骤] {step_info}")
        
    def test_valid_login(self, page):
        """测试有效登录"""
        self.test_start_time = time.time()
        print("[测试开始] test_valid_login", flush=True)
        
        if page is None:
            pytest.skip("Playwright 不可用")
            
        router_cfg = self.config.get('router', {})
        username = router_cfg.get('username', 'admin')
        password = router_cfg.get('password', 'admin123')
        
        self._log_step("打开登录页面")
        login_page = LoginPage(page)
        
        self._log_step(f"输入用户名: {username}")
        self._log_step(f"输入密码: {len(password) * '*'}")
        self._log_step("点击登录")
        
        result = login_page.login(username, password)
        
        self._log_step("验证登录成功" if result else "登录失败", "success" if result else "error")
        
        duration = time.time() - self.test_start_time
        self._log_step(f"执行耗时: {duration:.2f}秒")
        print("[测试结束] test_valid_login - 成功" if result else "[测试结束] test_valid_login - 失败", flush=True)
        
        assert result is True, "有效账号登录应该成功"
        
        # 检查登录状态
        login_status = login_page.is_login_successful()
        assert login_status == True, "登录后应该跳转到主页面"
        
    # ====================== 无效登录（参数化） ======================
    # 读取无效登录场景
    _invalid_cases = YamlReader().read_yaml("data/login_data.yaml").get("invalid_login", [])

    @pytest.mark.parametrize(
        "username,password,expected_error",
        [
            (case["username"], case["password"], case.get("error_message", "账号或密码错误"))
            for case in _invalid_cases
        ],
        ids=[case.get("description", f"{case.get('username') or '空'}-{case.get('password') or '空'}") for case in _invalid_cases]
    )
    def test_invalid_login_cases(self, page, username, password, expected_error):
        """使用 YAML 数据驱动的无效登录场景"""
        self.test_start_time = time.time()
        print(f"[测试开始] test_invalid_login ({username}/{password})", flush=True)
        if page is None:
            pytest.skip("Playwright 不可用")

        login_page = LoginPage(page)
        self._log_step(f"尝试登录: 用户名={username or '空'}, 密码={'*' * len(password) if password else '空'}")

        result = login_page.login(username, password)

        # 断言：登录应失败
        assert result is False, "预期登录失败，但实际登录成功"

        # 获取实际提示文本
        actual_msg = login_page.get_error_message()
        self._log_step(f"获取错误提示: {actual_msg}")

        # 如果 YAML 配置了期望提示，则必须匹配；否则只要有任何错误提示即可
        if expected_error:
            assert expected_error in actual_msg, f"期望提示 '{expected_error}', 实际 '{actual_msg}'"
        else:
            assert actual_msg, "未检测到错误提示"

        self._log_step("验证错误提示成功", "success")

        duration = time.time() - self.test_start_time
        self._log_step(f"执行耗时: {duration:.2f}秒")
        print("[测试结束] test_invalid_login", flush=True)