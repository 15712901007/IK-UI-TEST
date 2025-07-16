# GUI主程序入口
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 确保必要的目录存在
os.makedirs("logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("reports/outputs", exist_ok=True)

try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
        QPushButton, QLabel, QTextEdit, QSpinBox, QCheckBox, 
        QGroupBox, QLineEdit, QSplitter, QTabWidget, QProgressBar, 
        QMessageBox, QStatusBar, QTableWidget, QTableWidgetItem, 
        QHeaderView, QGridLayout, QListWidget, QListWidgetItem
    )
    from PySide6.QtCore import Qt, QThread, Signal, QTimer, QDateTime
    from PySide6.QtGui import QFont, QTextCursor
    
    # 导入项目模块
    try:
        from utils.logger import Logger
        from utils.yaml_reader import YamlReader
        from utils.test_runner import TestRunner
    except ImportError as e:
        print(f"导入模块失败: {e}")
        # 创建简单的替代类
        class Logger:
            def get_logger(self):
                import logging
                logging.basicConfig(level=logging.INFO)
                return logging.getLogger("RouterTest")
        
        class YamlReader:
            def read_yaml(self, file_path):
                return {}
            def write_yaml(self, file_path, data):
                return True
        
        class TestRunner:
            def run_tests(self, **kwargs):
                return {'success': False, 'message': '测试模块未正确安装'}
            def stop_tests(self):
                pass

    class TestExecutionThread(QThread):
        """测试执行线程"""
        
        progress_update = Signal(str)
        log_update = Signal(str)
        result_update = Signal(dict)
        finished_signal = Signal(bool, str, dict)
        
        def __init__(self, test_config):
            super().__init__()
            self.test_config = test_config
            self.test_runner = TestRunner()
            self._is_running = True
            
        def run(self):
            """执行测试"""
            try:
                self.progress_update.emit("🚀 开始执行测试...")
                self.log_update.emit("🔧 初始化测试环境...")
                
                # 执行真实的测试
                results = self.test_runner.run_tests(
                    test_config=self.test_config,
                    progress_callback=self.progress_update.emit,
                    log_callback=self.log_update.emit,
                    result_callback=self.result_update.emit
                )
                
                if self._is_running:
                    success = results.get('success', False)
                    message = results.get('message', '测试完成')
                    self.finished_signal.emit(success, message, results)
                    
            except Exception as e:
                if self._is_running:
                    self.finished_signal.emit(False, f"测试执行失败: {e}", {})
                    
        def stop(self):
            """停止测试"""
            self._is_running = False
            self.test_runner.stop_tests()

    class MainWindow(QMainWindow):
        """主窗口类"""
        
        def __init__(self):
            super().__init__()
            self.logger = Logger().get_logger()
            self.yaml_reader = YamlReader()
            self.test_thread = None
            self.test_results = {}
            
            self.init_ui()
            self.load_config()
            self.setup_timer()
            
        def init_ui(self):
            """初始化界面"""
            self.setWindowTitle("路由器自动化测试工具 v1.0.0")
            self.setGeometry(100, 100, 1400, 900)
            
            # 中央组件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # 主布局
            main_layout = QHBoxLayout(central_widget)
            
            # 创建左右面板
            left_panel = self.create_left_panel()
            right_panel = self.create_right_panel()
            
            # 分割器
            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(left_panel)
            splitter.addWidget(right_panel)
            splitter.setSizes([450, 950])
            
            main_layout.addWidget(splitter)
            
            # 状态栏
            self.status_bar = self.statusBar()
            self.status_bar.showMessage("就绪")
            
            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.status_bar.addPermanentWidget(self.progress_bar)
            
            # 时间标签
            self.time_label = QLabel()
            self.status_bar.addPermanentWidget(self.time_label)
            
        def create_left_panel(self):
            """创建左侧配置面板"""
            panel = QWidget()
            layout = QVBoxLayout(panel)
            
            # 路由器配置组
            router_group = QGroupBox("🌐 路由器配置")
            router_layout = QGridLayout(router_group)
            
            # IP地址
            router_layout.addWidget(QLabel("IP地址:"), 0, 0)
            self.ip_input = QLineEdit("10.66.0.40")
            router_layout.addWidget(self.ip_input, 0, 1)
            
            # 用户名
            router_layout.addWidget(QLabel("用户名:"), 1, 0)
            self.username_input = QLineEdit("admin")
            router_layout.addWidget(self.username_input, 1, 1)
            
            # 密码
            router_layout.addWidget(QLabel("密码:"), 2, 0)
            self.password_input = QLineEdit("admin123")
            self.password_input.setEchoMode(QLineEdit.Password)
            router_layout.addWidget(self.password_input, 2, 1)
            
            # 显示密码复选框
            self.show_password_checkbox = QCheckBox("显示密码")
            self.show_password_checkbox.toggled.connect(self.toggle_password_visibility)
            router_layout.addWidget(self.show_password_checkbox, 3, 1)
            
            layout.addWidget(router_group)
            
            # 测试配置组
            test_group = QGroupBox("⚙️ 测试配置")
            test_layout = QGridLayout(test_group)
            
            # 测试功能选择
            test_layout.addWidget(QLabel("测试功能:"), 0, 0)
            self.function_list = QListWidget()
            self.function_list.setMaximumHeight(120)
            for name in ["全部功能", "登录测试", "VLAN设置", "端口映射", "ACL规则", "终端分组"]:
                item = QListWidgetItem(name)
                item.setCheckState(getattr(Qt, 'Unchecked', 0))  # type: ignore
                self.function_list.addItem(item)
            test_layout.addWidget(self.function_list, 0, 1)
            
            # 全选/取消全选按钮
            func_btn_layout = QHBoxLayout()
            self.select_all_btn = QPushButton("全选")
            self.select_all_btn.clicked.connect(self.select_all_functions)
            func_btn_layout.addWidget(self.select_all_btn)
            self.clear_all_btn = QPushButton("取消全选")
            self.clear_all_btn.clicked.connect(self.clear_all_functions)
            func_btn_layout.addWidget(self.clear_all_btn)
            test_layout.addLayout(func_btn_layout, 1, 1)
            
            # 循环次数（行号 +1 因为多加了一行按钮）
            test_layout.addWidget(QLabel("循环次数:"), 2, 0)
            self.cycles_spinbox = QSpinBox()
            self.cycles_spinbox.setMinimum(1)
            self.cycles_spinbox.setMaximum(100)
            self.cycles_spinbox.setValue(1)
            test_layout.addWidget(self.cycles_spinbox, 2, 1)
            
            # 浏览器设置 - 默认不选择无头模式，这样可以看到浏览器
            self.headless_checkbox = QCheckBox("无头模式")
            self.headless_checkbox.setChecked(False)  # 默认显示浏览器
            test_layout.addWidget(self.headless_checkbox, 3, 0, 1, 2)
            
            self.screenshot_checkbox = QCheckBox("失败时截图")
            self.screenshot_checkbox.setChecked(True)
            test_layout.addWidget(self.screenshot_checkbox, 4, 0, 1, 2)
            
            self.video_checkbox = QCheckBox("录制视频")
            test_layout.addWidget(self.video_checkbox, 5, 0, 1, 2)
            
            # 详细日志开关 - 样式与其他复选框一致
            self.detail_log_checkbox = QCheckBox("显示详细日志")
            self.detail_log_checkbox.setChecked(True)  # 默认显示详细日志
            self.detail_log_checkbox.setToolTip("开启：显示页面操作详细日志\n关闭：只显示测试步骤")
            # 移除特殊红色高亮样式，使用默认样式
            # test_layout.addWidget(self.detail_log_checkbox, 5, 0, 1, 2)
            test_layout.addWidget(self.detail_log_checkbox, 6, 0, 1, 2)
            
            layout.addWidget(test_group)
            
            # 测试信息组
            info_group = QGroupBox("📝 测试信息")
            info_layout = QGridLayout(info_group)
            
            # 测试版本
            info_layout.addWidget(QLabel("测试版本:"), 0, 0)
            self.version_input = QLineEdit("1.0.0")
            info_layout.addWidget(self.version_input, 0, 1)
            
            # 测试人员
            info_layout.addWidget(QLabel("测试人员:"), 1, 0)
            self.tester_input = QLineEdit("自动化测试")
            info_layout.addWidget(self.tester_input, 1, 1)
            
            # 测试环境
            info_layout.addWidget(QLabel("测试环境:"), 2, 0)
            self.environment_input = QLineEdit("测试环境")
            info_layout.addWidget(self.environment_input, 2, 1)
            
            layout.addWidget(info_group)
            
            # 通知配置组
            notify_group = QGroupBox("📢 通知配置")
            notify_layout = QGridLayout(notify_group)
            
            self.wechat_notify_checkbox = QCheckBox("企业微信通知")
            notify_layout.addWidget(self.wechat_notify_checkbox, 0, 0, 1, 2)
            
            notify_layout.addWidget(QLabel("Webhook:"), 1, 0)
            self.webhook_input = QLineEdit()
            self.webhook_input.setPlaceholderText("https://qyapi.weixin.qq.com/...")
            notify_layout.addWidget(self.webhook_input, 1, 1)
            
            layout.addWidget(notify_group)
            
            # 按钮组
            button_layout = QVBoxLayout()
            
            # 主要按钮
            self.start_button = QPushButton("🚀 开始测试")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.start_button.clicked.connect(self.start_test)
            button_layout.addWidget(self.start_button)
            
            self.stop_button = QPushButton("⏹️ 停止测试")
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.stop_button.clicked.connect(self.stop_test)
            self.stop_button.setEnabled(False)
            button_layout.addWidget(self.stop_button)
            
            # 辅助按钮
            self.report_button = QPushButton("📊 查看报告")
            self.report_button.clicked.connect(self.view_report)
            button_layout.addWidget(self.report_button)
            
            self.config_button = QPushButton("⚙️ 保存配置")
            self.config_button.clicked.connect(self.save_config)
            button_layout.addWidget(self.config_button)
            
            self.clear_button = QPushButton("🗑️ 清空日志")
            self.clear_button.clicked.connect(self.clear_logs)
            button_layout.addWidget(self.clear_button)
            
            layout.addLayout(button_layout)
            layout.addStretch()
            
            return panel
            
        def create_right_panel(self):
            """创建右侧监控面板"""
            panel = QWidget()
            layout = QVBoxLayout(panel)
            
            # 标签页
            self.tab_widget = QTabWidget()
            
            # 实时日志标签页
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setFont(QFont("Consolas", 9))
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border: 1px solid #ccc;
                }
            """)
            self.tab_widget.addTab(self.log_text, "📋 实时日志")
            
            # 测试结果标签页
            self.result_table = QTableWidget()
            self.result_table.setColumnCount(6)
            self.result_table.setHorizontalHeaderLabels([
                "测试用例", "状态", "开始时间", "结束时间", "耗时", "备注"
            ])
            self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.tab_widget.addTab(self.result_table, "📈 测试结果")
            
            # 统计信息标签页
            self.stats_text = QTextEdit()
            self.stats_text.setReadOnly(True)
            self.tab_widget.addTab(self.stats_text, "📊 统计信息")
            
            # 配置信息标签页
            self.config_text = QTextEdit()
            self.config_text.setReadOnly(True)
            self.tab_widget.addTab(self.config_text, "⚙️ 配置信息")
            
            layout.addWidget(self.tab_widget)
            
            return panel
        
        def setup_timer(self):
            """设置定时器"""
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_time)
            self.timer.start(1000)  # 每秒更新一次
            
        def update_time(self):
            """更新时间显示"""
            current_time = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            self.time_label.setText(current_time)
            
        def toggle_password_visibility(self, checked):
            """切换密码可见性"""
            if checked:
                self.password_input.setEchoMode(QLineEdit.Normal)
            else:
                self.password_input.setEchoMode(QLineEdit.Password)
        
        def load_config(self):
            """加载配置"""
            try:
                config = self.yaml_reader.read_yaml("config/test_config.yaml")
                
                if config:
                    # 路由器配置
                    router_config = config.get('router', {})
                    self.ip_input.setText(router_config.get('ip', '10.66.0.40'))
                    self.username_input.setText(router_config.get('username', 'admin'))
                    self.password_input.setText(router_config.get('password', 'admin123'))
                    
                    # 浏览器配置
                    browser_config = config.get('browser', {})
                    self.headless_checkbox.setChecked(browser_config.get('headless', False))
                    
                    # 测试配置
                    test_config = config.get('test_settings', {})
                    self.screenshot_checkbox.setChecked(
                        test_config.get('screenshot_on_failure', True)
                    )
                    self.video_checkbox.setChecked(
                        test_config.get('video_on_failure', False)
                    )
                    self.detail_log_checkbox.setChecked(
                        test_config.get('show_detail_logs', True)
                    )
                    
                # 显示当前配置
                self.update_config_display()
                self.log_message("✅ 配置加载完成")
                    
            except Exception as e:
                self.log_message(f"❌ 加载配置失败: {e}")
        
        def save_config(self):
            """保存配置"""
            try:
                config = {
                    'router': {
                        'ip': self.ip_input.text(),
                        'username': self.username_input.text(),
                        'password': self.password_input.text(),
                        'timeout': 30,
                        'retry_times': 3
                    },
                    'browser': {
                        'headless': self.headless_checkbox.isChecked(),
                        'browser_type': 'chromium',
                        'viewport': {
                            'width': 1920,
                            'height': 1080
                        }
                    },
                    'test_settings': {
                        'screenshot_on_failure': self.screenshot_checkbox.isChecked(),
                        'video_on_failure': self.video_checkbox.isChecked(),
                        'show_detail_logs': self.detail_log_checkbox.isChecked(),
                        'parallel_workers': 1,
                        'retry_failed': 1
                    },
                    'report': {
                        'title': '路由器自动化测试报告',
                        'language': 'zh-CN',
                        'include_screenshots': True,
                        'include_logs': True
                    }
                }
                
                success = self.yaml_reader.write_yaml("config/test_config.yaml", config)
                
                if success:
                    QMessageBox.information(self, "成功", "配置保存成功！")
                    self.log_message("✅ 配置保存成功")
                    self.update_config_display()
                else:
                    QMessageBox.warning(self, "失败", "配置保存失败！")
                    
            except Exception as e:
                self.log_message(f"❌ 保存配置失败: {e}")
                QMessageBox.critical(self, "错误", f"保存配置失败: {e}")
        
        def update_config_display(self):
            """更新配置显示"""
            from datetime import datetime
            
            detail_log_status = "开启 ✅" if self.detail_log_checkbox.isChecked() else "关闭 ❌"
            detail_log_desc = "显示页面操作详细日志" if self.detail_log_checkbox.isChecked() else "只显示测试执行步骤"
            
            config_info = f"""
当前配置信息:

📡 路由器配置:
  - IP地址: {self.ip_input.text()}
  - 用户名: {self.username_input.text()}
  - 密码: {'*' * len(self.password_input.text())}

🌐 浏览器配置:
  - 无头模式: {self.headless_checkbox.isChecked()}
  - 失败截图: {self.screenshot_checkbox.isChecked()}
  - 录制视频: {self.video_checkbox.isChecked()}

🧪 测试配置:
  - 测试功能: {', '.join([self.function_list.item(i).text() for i in range(self.function_list.count()) if self.function_list.item(i).checkState()==getattr(Qt,'Checked',2)] or ['全部功能'])}
  - 循环次数: {self.cycles_spinbox.value()}
  - 详细日志: {detail_log_status}
  - 测试版本: {self.version_input.text()}
  - 测试人员: {self.tester_input.text()}
  - 测试环境: {self.environment_input.text()}

📢 通知配置:
  - 企业微信通知: {self.wechat_notify_checkbox.isChecked()}
  - Webhook: {self.webhook_input.text() or '未配置'}

💡 日志说明:
  - [执行步骤]: 测试步骤信息（始终显示）
  - [日志]: 页面操作详细日志（{detail_log_desc}）
  - 📝: pytest系统信息（始终显示）

💡 提示: 取消勾选"无头模式"可以看到浏览器执行过程

更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            self.config_text.setText(config_info)
        
        def start_test(self):
            """开始测试"""
            try:
                # 验证配置
                if not self.validate_config():
                    return
                    
                # 禁用开始按钮，启用停止按钮
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                # 显示进度条
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # 清空之前的结果
                self.clear_results()
                
                # 获取测试配置
                test_config = self.get_test_config()
                
                # 更新状态
                self.status_bar.showMessage("测试执行中...")
                self.log_message("🚀 开始执行测试...")
                test_functions_display = ', '.join(test_config['test_function'])
                self.log_message(f"📋 测试配置: {test_functions_display}, 循环 {test_config['cycles']} 次")
                
                if not test_config['browser']['headless']:
                    self.log_message("👁️ 浏览器可见模式，您可以看到测试执行过程")
                else:
                    self.log_message("🔇 无头模式，浏览器将在后台运行")
                
                if test_config.get('show_detail_logs', True):
                    self.log_message("📝 详细日志模式：将显示页面操作和测试步骤")
                else:
                    self.log_message("📝 简化日志模式：只显示测试执行步骤")
                
                # 启动测试线程
                self.test_thread = TestExecutionThread(test_config)
                self.test_thread.progress_update.connect(self.update_progress)
                self.test_thread.log_update.connect(self.log_message)
                self.test_thread.result_update.connect(self.update_result)
                self.test_thread.finished_signal.connect(self.test_finished)
                self.test_thread.start()
                
            except Exception as e:
                self.log_message(f"❌ 启动测试失败: {e}")
                QMessageBox.critical(self, "错误", f"启动测试失败: {e}")
                self.test_finished(False, str(e), {})
        
        def validate_config(self):
            """验证配置"""
            if not self.ip_input.text().strip():
                QMessageBox.warning(self, "配置错误", "请输入路由器IP地址！")
                return False
                
            if not self.username_input.text().strip():
                QMessageBox.warning(self, "配置错误", "请输入用户名！")
                return False
                
            if not self.password_input.text().strip():
                QMessageBox.warning(self, "配置错误", "请输入密码！")
                return False
                
            return True
        
        def get_test_config(self):
            """获取测试配置"""
            return {
                'router': {
                    'ip': self.ip_input.text(),
                    'username': self.username_input.text(),
                    'password': self.password_input.text()
                },
                'test_function': [self.function_list.item(i).text() for i in range(self.function_list.count()) if self.function_list.item(i).checkState()==getattr(Qt,'Checked',2)] or ['全部功能'],
                'cycles': self.cycles_spinbox.value(),
                'browser': {
                    'headless': self.headless_checkbox.isChecked(),
                    'screenshot_on_failure': self.screenshot_checkbox.isChecked(),
                    'video_on_failure': self.video_checkbox.isChecked()
                },
                'show_detail_logs': self.detail_log_checkbox.isChecked(),  # 关键配置项
                'test_info': {
                    'version': self.version_input.text(),
                    'tester': self.tester_input.text(),
                    'environment': self.environment_input.text()
                },
                'notification': {
                    'wechat_enabled': self.wechat_notify_checkbox.isChecked(),
                    'webhook_url': self.webhook_input.text()
                }
            }
        
        def stop_test(self):
            """停止测试"""
            if self.test_thread and self.test_thread.isRunning():
                self.log_message("⏹️ 正在停止测试...")
                self.test_thread.stop()
                self.test_thread.wait(3000)  # 等待3秒
                
            self.test_finished(False, "用户取消测试", {})
        
        def test_finished(self, success: bool, message: str, results: dict):
            """测试完成"""
            # 恢复按钮状态
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            # 隐藏进度条
            self.progress_bar.setVisible(False)
            
            # 保存测试结果
            self.test_results = results
            
            # 更新状态栏
            if success:
                self.status_bar.showMessage("✅ 测试完成")
                self.log_message(f"✅ 测试成功完成: {message}")
            else:
                self.status_bar.showMessage("❌ 测试失败")
                self.log_message(f"❌ 测试失败: {message}")
            
            # 更新统计信息
            self.update_statistics(results)
            
            # 显示报告文件路径
            report_file = results.get('report_file')
            if report_file and os.path.exists(report_file):
                self.log_message(f"📊 测试报告已生成: {report_file}")
            
            # 发送通知
            if self.wechat_notify_checkbox.isChecked() and self.webhook_input.text():
                self.send_wechat_notification(success, message, results)
            
            # 显示完成消息
            if success:
                reply = QMessageBox.question(
                    self, "测试完成", 
                    f"测试已成功完成！\n\n{message}\n\n是否立即查看测试报告？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.view_report()
            else:
                QMessageBox.warning(self, "测试失败", f"测试失败！\n\n{message}")
        
        def update_progress(self, message: str):
            """更新进度"""
            self.log_message(message)
            
            # 简单的进度计算（基于消息内容）
            if "%" in message:
                try:
                    percent = int(message.split("%")[0].split()[-1])
                    self.progress_bar.setValue(percent)
                except:
                    pass
        
        def log_message(self, message: str):
            """记录日志消息（支持详细日志过滤）"""
            # 先将可能存在的 "\uXXXX" 转义序列还原成真实中文，防止 GUI 显示乱码
            import re
            def _decode_unicode_escape(s: str):
                try:
                    if "\\u" in s:
                        return re.sub(r"\\u[0-9a-fA-F]{4}", lambda m: chr(int(m.group(0)[2:], 16)), s)
                    return s
                except Exception:
                    return s

            message = _decode_unicode_escape(message)

            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"

            # 过滤详细日志：只显示关键步骤和结果
            if not self.detail_log_checkbox.isChecked():
                # 只保留含有"执行步骤"、"❌"、"✅"、"测试失败"、"测试成功"、"报告"、"已清空"等关键字的日志
                keywords = ["执行步骤", "❌", "✅", "测试失败", "测试成功", "报告", "已清空", "开始执行测试", "停止测试", "加载完成", "保存成功", "失败", "错误", "提示"]
                if not any(k in message for k in keywords):
                    return  # 过滤掉详细日志

            self.log_text.append(formatted_message)
            # 自动滚动到底部
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_text.setTextCursor(cursor)
            # 确保界面更新
            self.log_text.repaint()
        
        def update_result(self, result: dict):
            """更新测试结果"""
            try:
                row = self.result_table.rowCount()
                self.result_table.insertRow(row)
                
                # 添加结果数据
                self.result_table.setItem(row, 0, QTableWidgetItem(result.get('test_case', '')))
                
                status = result.get('status', 'unknown')
                status_item = QTableWidgetItem(status)
                if status == 'PASSED':
                    status_item.setBackground(Qt.green)
                elif status == 'FAILED':
                    status_item.setBackground(Qt.red)
                else:
                    status_item.setBackground(Qt.yellow)
                self.result_table.setItem(row, 1, status_item)
                
                self.result_table.setItem(row, 2, QTableWidgetItem(result.get('start_time', '')))
                self.result_table.setItem(row, 3, QTableWidgetItem(result.get('end_time', '')))
                self.result_table.setItem(row, 4, QTableWidgetItem(result.get('duration', '')))
                self.result_table.setItem(row, 5, QTableWidgetItem(result.get('message', '')))
                
            except Exception as e:
                self.log_message(f"❌ 更新结果失败: {e}")
        
        def update_statistics(self, results: dict):
            """更新统计信息"""
            try:
                from datetime import datetime
                stats = results.get('statistics', {})
                
                stats_info = f"""
📊 测试统计信息

🕐 执行时间:
  - 开始时间: {results.get('start_time', '未知')}
  - 结束时间: {results.get('end_time', '未知')}
  - 总耗时: {results.get('total_duration', '未知')}

📈 测试结果:
  - 总用例数: {stats.get('total', 0)}
  - 成功数量: {stats.get('passed', 0)}
  - 失败数量: {stats.get('failed', 0)}
  - 跳过数量: {stats.get('skipped', 0)}
  - 错误数量: {stats.get('error', 0)}

📊 成功率: {stats.get('success_rate', 0):.1f}%

🔧 测试环境:
  - 路由器IP: {self.ip_input.text()}
  - 测试版本: {self.version_input.text()}
  - 测试人员: {self.tester_input.text()}
  - 浏览器模式: {'无头模式' if self.headless_checkbox.isChecked() else '有头模式'}
  - 详细日志: {'开启' if self.detail_log_checkbox.isChecked() else '关闭'}

📝 详细信息:
{results.get('summary', '暂无详细信息')}

📄 报告文件: {results.get('report_file', '未生成')}

更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                self.stats_text.setText(stats_info)
                
            except Exception as e:
                self.log_message(f"❌ 更新统计信息失败: {e}")
        
        def send_wechat_notification(self, success: bool, message: str, results: dict):
            """发送企业微信通知"""
            try:
                # 这里可以实现真实的企业微信通知
                self.log_message("📢 企业微信通知发送成功（模拟）")
                    
            except Exception as e:
                self.log_message(f"❌ 发送企业微信通知失败: {e}")
        
        def clear_logs(self):
            """清空日志"""
            self.log_text.clear()
            self.result_table.setRowCount(0)
            self.stats_text.clear()
            self.log_message("🗑️ 日志已清空")
        
        def clear_results(self):
            """清空测试结果"""
            self.result_table.setRowCount(0)
            self.stats_text.clear()
            self.test_results = {}
        
        def view_report(self):
            """查看测试报告"""
            reports_dir = Path("reports/outputs")
            
            if not reports_dir.exists():
                QMessageBox.information(self, "提示", "报告目录不存在，请先运行测试！")
                return
            
            # 查找最新的报告文件
            report_files = list(reports_dir.glob("*.html"))
            
            if not report_files:
                QMessageBox.information(self, "提示", "没有找到测试报告，请先运行测试！")
                return
            
            # 按修改时间排序，获取最新的报告
            latest_report = max(report_files, key=os.path.getmtime)
            
            try:
                # 在默认浏览器中打开报告
                os.startfile(str(latest_report))
                self.log_message(f"📊 已打开测试报告: {latest_report.name}")
            except Exception as e:
                try:
                    # 尝试其他方式打开
                    import webbrowser
                    webbrowser.open(f"file://{latest_report.absolute()}")
                    self.log_message(f"📊 已打开测试报告: {latest_report.name}")
                except Exception as e2:
                    QMessageBox.warning(self, "错误", f"无法打开测试报告: {e}")
        
        def closeEvent(self, event):
            """窗口关闭事件"""
            if self.test_thread and self.test_thread.isRunning():
                reply = QMessageBox.question(
                    self, "确认", 
                    "测试正在运行中，确定要退出吗？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.test_thread.stop()
                    self.test_thread.wait(3000)
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()

        def select_all_functions(self):
            """全选功能"""
            for i in range(self.function_list.count()):
                self.function_list.item(i).setCheckState(getattr(Qt, 'Checked', 2))  # type: ignore

        def clear_all_functions(self):
            """取消全选功能"""
            for i in range(self.function_list.count()):
                self.function_list.item(i).setCheckState(getattr(Qt, 'Unchecked', 0))  # type: ignore

    def main():
        """主程序入口"""
        app = QApplication(sys.argv)
        app.setApplicationName("路由器自动化测试工具")
        app.setApplicationVersion("1.0.0")
        
        # 设置应用样式
        app.setStyle("Fusion")
        
        # 创建主窗口
        try:
            main_window = MainWindow()
            main_window.show()
            
            # 显示欢迎消息
            main_window.log_message("🎉 欢迎使用路由器自动化测试工具！")
            main_window.log_message("📝 请先配置路由器信息，然后点击'开始测试'")
            main_window.log_message("💡 提示：取消勾选'无头模式'可以看到浏览器执行过程")
            main_window.log_message("🔧 提示：取消勾选'显示详细日志'只显示测试步骤")
            main_window.log_message("🔧 首次使用请确保已安装：pip install -r requirements.txt && playwright install chromium")
            
            sys.exit(app.exec())
            
        except Exception as e:
            QMessageBox.critical(None, "启动错误", f"程序启动失败: {e}")

except ImportError as e:
    def main():
        print("=" * 60)
        print("🚨 缺少必要的依赖包！")
        print("=" * 60)
        print(f"错误信息: {e}")
        print("\n📋 请按以下步骤安装依赖：")
        print("1. pip install PySide6")
        print("2. pip install playwright")
        print("3. pip install pytest")
        print("4. pip install PyYAML")
        print("5. pip install Jinja2")
        print("6. playwright install chromium")
        print("\n📝 或者运行: pip install -r requirements.txt")
        print("=" * 60)
        input("按任意键继续...")

if __name__ == "__main__":
    main()