# 截图工具
from playwright.sync_api import Page
from pathlib import Path
from datetime import datetime

class ScreenshotHelper:
    """截图助手类"""
    
    def __init__(self, page: Page):
        self.page = page
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # 简单的日志记录
        try:
            from utils.logger import Logger
            self.logger = Logger().get_logger()
        except:
            import logging
            self.logger = logging.getLogger("screenshot")
    
    def take_screenshot(self, name: str = None):
        """截图"""
        try:
            if name is None:
                name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
            
            screenshot_path = self.screenshot_dir / f"{name}.png"
            self.page.screenshot(path=str(screenshot_path), full_page=True)
            
            self.logger.info(f"截图保存: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"截图失败: {e}")
            return None
    
    def take_element_screenshot(self, selector: str, name: str = None):
        """元素截图"""
        try:
            element = self.page.query_selector(selector)
            if not element:
                self.logger.error(f"元素不存在: {selector}")
                return None
            
            if name is None:
                name = f"element_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
            
            screenshot_path = self.screenshot_dir / f"{name}.png"
            element.screenshot(path=str(screenshot_path))
            
            self.logger.info(f"元素截图保存: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"元素截图失败: {e}")
            return None