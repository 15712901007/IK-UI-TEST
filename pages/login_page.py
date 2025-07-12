# 登录页面类
from pages.base_page import BasePage
from playwright.sync_api import Page
import time
from utils.yaml_reader import YamlReader

class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        
        # 动态读取路由器IP，默认 10.66.0.40
        cfg = YamlReader().read_yaml("config/test_config.yaml") or {}
        ip_addr = cfg.get("router", {}).get("ip", "10.66.0.40")

        # 页面元素选择器
        self.login_url = f"http://{ip_addr}/login#/login"
        self.username_role = ("textbox", "用户名")
        self.password_role = ("textbox", "密码")
        self.login_button_role = ("button", "登录")
        
    def login(self, username: str, password: str):
        """执行登录操作"""
        try:
            self.logger.info(f"开始登录，用户名: {username}")
            
            # 导航到登录页面
            if not self.navigate_to(self.login_url):
                return False
                
            # 等待页面加载
            time.sleep(2)
                
            # 输入用户名
            if not self.input_text_by_role(self.username_role[0], self.username_role[1], username):
                return False
                
            # 输入密码
            if not self.input_text_by_role(self.password_role[0], self.password_role[1], password):
                return False
                
            # 点击登录按钮
            if not self.click_by_role(self.login_button_role[0], self.login_button_role[1]):
                return False
                
            # 等待页面跳转
            time.sleep(3)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # 检查是否登录成功
            if self.is_login_successful():
                self.logger.info(f"登录成功: {username}")
                return True
            else:
                error_msg = self.get_error_message()
                self.logger.error(f"登录失败: {error_msg}")
                self.screenshot.take_screenshot("login_failed")
                return False
                
        except Exception as e:
            self.logger.error(f"登录过程出错: {e}")
            self.screenshot.take_screenshot("login_error")
            return False
            
    def is_login_successful(self):
        """检查是否登录成功"""
        try:
            # 等待页面加载
            time.sleep(2)
            
            # 检查URL变化
            current_url = self.page.url
            if "login" not in current_url:
                self.logger.info("URL已跳转，登录可能成功")
                return True
            
            # 检查页面元素
            success_indicators = [
                "网络设置",  # 导航菜单
                "系统管理",  # 系统管理菜单
                "高级设置",  # 高级设置菜单
            ]
            
            for indicator in success_indicators:
                try:
                    # 检查是否有菜单文本
                    element = self.page.locator(f"text={indicator}").first
                    if element.is_visible(timeout=5000):
                        self.logger.info(f"找到成功指示器: {indicator}")
                        return True
                except:
                    continue
            
            # 检查常见的登录成功元素
            success_selectors = [
                ".main-content",
                ".dashboard", 
                "#main",
                ".layout-main",
                "[class*='main']",
                "[class*='dashboard']"
            ]
            
            for selector in success_selectors:
                if self.is_element_visible(selector):
                    self.logger.info(f"找到成功指示器: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查登录状态失败: {e}")
            return False
        
    def get_error_message(self):
        """获取错误消息"""
        # 先尝试常见固定文案，以提高匹配准确率
        common_errors = [
            "用户名或密码错误", "账号或密码错误", "请输入用户名", "请输入密码"
        ]
        for text in common_errors:
            try:
                if self.page.get_by_text(text, exact=True).is_visible(timeout=2000):
                    return text
            except:
                pass

        error_selectors = [
            ".error-message",
            ".login-error", 
            ".alert-danger",
            ".ant-message-error",
            ".el-message--error",
            "[class*='error']",
            "[class*='alert']"
        ]
        
        for selector in error_selectors:
            try:
                element = self.page.query_selector(selector)
                if element and element.is_visible():
                    return element.text_content()
            except:
                continue
        
        return "登录失败，未知错误"
        
    def logout(self):
        """退出登录"""
        try:
            logout_selectors = [
                "#logout",
                ".logout",
                "[data-action='logout']",
                "text=退出",
                "text=登出"
            ]
            
            for selector in logout_selectors:
                if self.is_element_visible(selector):
                    return self.click_element(selector)
            
            # 如果找不到退出按钮，尝试直接跳转到登录页面
            return self.navigate_to(self.login_url)
            
        except Exception as e:
            self.logger.error(f"退出登录失败: {e}")
            return False

    def has_error_message(self, text: str) -> bool:
        """检查页面上是否存在指定错误提示"""
        try:
            # 使用 wait_for_selector 可检测存在即可，不要求先可见
            self.page.wait_for_selector(f"text={text}", timeout=3000)
            return True
        except:
            return False