# pytest配置文件
import pytest
import sys
import os
from pathlib import Path
import ctypes
import time

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 确保必要的目录存在
os.makedirs(project_root / "logs", exist_ok=True)
os.makedirs(project_root / "screenshots", exist_ok=True)
os.makedirs(project_root / "reports" / "outputs", exist_ok=True)

def get_screen_size():
    """获取电脑屏幕分辨率"""
    try:
        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        return screensize
    except:
        # 如果获取失败，返回默认值
        return (2880, 1800)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from utils.yaml_reader import YamlReader
    from utils.logger import Logger
    from pages.login_page import LoginPage
except ImportError:
    # 如果导入失败，创建简单的替代类
    class YamlReader:
        def read_yaml(self, file_path):
            return {
                'router': {'ip': '10.66.0.40', 'username': 'admin', 'password': 'admin123'},
                'browser': {'headless': False, 'viewport': {'width': 1920, 'height': 1080}}
            }
    
    class Logger:
        def get_logger(self):
            import logging
            return logging.getLogger("test")
    
    class LoginPage:
        def __init__(self, page):
            self.page = page
        def login(self, username, password):
            return False

@pytest.fixture(scope="session")
def config():
    """加载测试配置"""
    yaml_reader = YamlReader()
    return yaml_reader.read_yaml("config/test_config.yaml")

@pytest.fixture(scope="session")
def test_data():
    """加载测试数据"""
    yaml_reader = YamlReader()
    return {
        'login': yaml_reader.read_yaml("data/login_data.yaml"),
        'vlan': yaml_reader.read_yaml("data/vlan_data.yaml"),
        'common': yaml_reader.read_yaml("data/common_data.yaml")
    }

if PLAYWRIGHT_AVAILABLE:
    @pytest.fixture(scope="session")
    def browser_context():
        """创建浏览器上下文 - 使用电脑实际分辨率"""
        with sync_playwright() as p:
            config = YamlReader().read_yaml("config/test_config.yaml")
            browser_config = config.get('browser', {})
            
            # 获取电脑实际分辨率
            screen_width, screen_height = get_screen_size()
            print(f"检测到屏幕分辨率: {screen_width}x{screen_height}")  # 移除emoji
            
            # 启动浏览器 - 使用实际屏幕分辨率
            browser = p.chromium.launch(
                headless=browser_config.get('headless', False),
                slow_mo=browser_config.get('slow_mo', 100),
                args=[
                    f'--window-size={screen_width},{screen_height}',
                    '--start-maximized',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # 创建上下文 - 使用实际屏幕分辨率
            context = browser.new_context(
                viewport={'width': screen_width, 'height': screen_height},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            yield context
            
            browser.close()

    @pytest.fixture(scope="session")
    def authenticated_page(browser_context, config):
        """Session级别的已登录页面 - 避免重复登录"""
        page = browser_context.new_page()
        
        # 获取并设置实际屏幕大小
        screen_width, screen_height = get_screen_size()
        page.set_viewport_size({"width": screen_width, "height": screen_height})
        
        # 执行一次登录
        login_page = LoginPage(page)
        router_config = config.get('router', {})
        
        print("Session级别登录开始...")  # 移除emoji
        success = login_page.login(
            router_config.get('username', 'admin'),
            router_config.get('password', 'admin123')
        )
        
        if not success:
            pytest.fail("Session级别登录失败，无法继续测试")
        
        print("Session级别登录成功，后续测试将复用此登录状态")  # 移除emoji
        
        yield page
        page.close()

    @pytest.fixture
    def page(browser_context):
        """创建独立页面 - 用于登录相关测试"""
        page = browser_context.new_page()
        
        # 获取并设置实际屏幕大小
        screen_width, screen_height = get_screen_size()
        page.set_viewport_size({"width": screen_width, "height": screen_height})
        
        yield page
        page.close()

    @pytest.fixture
    def logged_in_page(authenticated_page):
        """已登录的页面 - 用于功能测试，复用Session登录状态"""
        return authenticated_page

else:
    # 如果Playwright不可用，创建模拟的fixture
    @pytest.fixture(scope="session")
    def browser_context():
        """模拟浏览器上下文"""
        return None

    @pytest.fixture(scope="session")
    def authenticated_page(browser_context, config):
        """模拟已登录页面"""
        return None

    @pytest.fixture
    def page(browser_context):
        """模拟页面"""
        return None

    @pytest.fixture
    def logged_in_page(authenticated_page):
        """模拟已登录页面"""
        return None

def pytest_configure(config):
    """pytest配置"""
    # 确保必要的目录存在
    os.makedirs("logs", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("reports/outputs", exist_ok=True)

def pytest_runtest_makereport(item, call):
    """测试报告钩子"""
    if call.when == "call":
        # 测试失败时的处理
        if call.excinfo is not None:
            try:
                logger = Logger().get_logger()
                logger.error(f"测试失败: {item.name}")
            except:
                print(f"测试失败: {item.name}")

def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    if not PLAYWRIGHT_AVAILABLE:
        # 如果Playwright不可用，跳过所有需要浏览器的测试
        skip_playwright = pytest.mark.skip(reason="Playwright not available")
        for item in items:
            if "page" in item.fixturenames:
                item.add_marker(skip_playwright)