# 基础页面类
from playwright.sync_api import Page, expect
from utils.logger import Logger
from utils.screenshot_helper import ScreenshotHelper
import time

class BasePage:
    def __init__(self, page: Page):
        self.page = page
        self.logger = Logger().get_logger()
        self.screenshot = ScreenshotHelper(page)
        
    def navigate_to(self, url: str):
        """导航到指定URL"""
        try:
            self.page.goto(url)
            self.page.wait_for_load_state("networkidle", timeout=10000)
            self.logger.info(f"成功导航到页面: {url}")
            return True
        except Exception as e:
            self.logger.error(f"导航失败: {e}")
            self.screenshot.take_screenshot("navigation_error")
            return False
            
    def wait_for_element(self, selector: str, timeout: int = 10000):
        """等待元素出现"""
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            return element
        except Exception as e:
            self.logger.error(f"等待元素失败 {selector}: {e}")
            return None
            
    def click_element(self, selector: str):
        """点击元素"""
        try:
            element = self.wait_for_element(selector)
            if element:
                element.click()
                self.logger.info(f"成功点击元素: {selector}")
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            self.logger.error(f"点击元素失败 {selector}: {e}")
            self.screenshot.take_screenshot("click_error")
            return False
            
    def click_by_role(self, role: str, name: str = None):
        """通过role点击元素"""
        try:
            if name:
                element = self.page.get_by_role(role, name=name)
            else:
                element = self.page.get_by_role(role)
            element.click()
            self.logger.info(f"成功点击元素 role={role}, name={name}")
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"点击元素失败 role={role}, name={name}: {e}")
            self.screenshot.take_screenshot("click_role_error")
            return False
            
    def input_text(self, selector: str, text: str):
        """输入文本 - 修复clear()方法问题"""
        try:
            # 使用Playwright的正确方式清空和填充文本
            self.page.fill(selector, text)
            self.logger.info(f"成功输入文本到 {selector}: {text}")
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败 {selector}: {e}")
            self.screenshot.take_screenshot("input_error")
            return False
            
    def input_text_by_role(self, role: str, name: str, text: str):
        """通过role输入文本"""
        try:
            element = self.page.get_by_role(role, name=name)
            element.fill(text)
            self.logger.info(f"成功输入文本 role={role}, name={name}: {text}")
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败 role={role}, name={name}: {e}")
            self.screenshot.take_screenshot("input_role_error")
            return False
            
    def get_text(self, selector: str):
        """获取元素文本"""
        try:
            element = self.wait_for_element(selector)
            if element:
                text = element.text_content()
                self.logger.info(f"获取文本 {selector}: {text}")
                return text
            return None
        except Exception as e:
            self.logger.error(f"获取文本失败 {selector}: {e}")
            return None
            
    def is_element_visible(self, selector: str):
        """检查元素是否可见"""
        try:
            element = self.page.query_selector(selector)
            if element and element.is_visible():
                return True
            return False
        except Exception as e:
            self.logger.error(f"检查元素可见性失败 {selector}: {e}")
            return False
            
    def wait_for_toast_message(self, timeout: int = 5000):
        """等待提示消息"""
        toast_selectors = [
            ".toast", ".message", ".alert", 
            ".notification", ".tips", "[class*='toast']",
            ".ant-message", ".el-message"
        ]
        
        for selector in toast_selectors:
            try:
                element = self.page.wait_for_selector(selector, timeout=timeout)
                if element:
                    message = element.text_content()
                    self.logger.info(f"收到提示消息: {message}")
                    return message
            except:
                continue
        return None
        
    def click_link_by_text(self, text: str):
        """通过文本点击链接"""
        try:
            self.page.get_by_role("link", name=text).click()
            self.logger.info(f"成功点击链接: {text}")
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"点击链接失败 {text}: {e}")
            self.screenshot.take_screenshot("click_link_error")
            return False
            
    def click_text_filter(self, text: str):
        """点击包含指定文本的元素"""
        try:
            self.page.locator("a").filter(has_text=text).click()
            self.logger.info(f"成功点击文本元素: {text}")
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"点击文本元素失败 {text}: {e}")
            self.screenshot.take_screenshot("click_text_error")
            return False