# 测试执行器 - 优化版本（支持详细日志显示）
import pytest
import sys
import os
import json
import subprocess
import threading
import queue
import time
import re
from pathlib import Path
from datetime import datetime
from utils.logger import Logger
from utils.yaml_reader import YamlReader
from utils.report_generator import ReportGenerator

class TestRunner:
    """测试执行器 - 优化版"""
    
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.project_root = Path(__file__).parent.parent
        self._stop_requested = False
        self._current_process = None
        self._show_detail_logs = True  # 默认显示详细日志
        
    def set_detail_logs(self, show_detail):
        """设置是否显示详细日志"""
        self._show_detail_logs = show_detail
        
    def run_tests(self, test_config, progress_callback=None, log_callback=None, result_callback=None):
        """运行测试"""
        self._stop_requested = False
        start_time = datetime.now()
        
        # 从配置中获取详细日志设置
        self._show_detail_logs = test_config.get('show_detail_logs', True)
        
        try:
            if log_callback:
                log_callback("🔧 正在更新测试配置...")
                
            # 更新配置文件
            self._update_test_config(test_config)
            
            if log_callback:
                log_callback("📋 构建测试参数...")
                
            # 构建pytest参数
            pytest_args, report_file = self._build_pytest_args(test_config)
            
            if log_callback:
                log_callback(f"🚀 开始执行测试，pytest报告：{report_file}")
            
            # 执行测试
            results = self._execute_tests(
                pytest_args, 
                test_config,
                progress_callback,
                log_callback,
                result_callback,
                report_file
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # 生成中文测试报告
            chinese_report_file = None
            try:
                if log_callback:
                    log_callback("📊 正在生成中文测试报告...")
                
                report_generator = ReportGenerator()
                chinese_report_file = report_generator.generate_report(
                    test_results={
                        'success': results.get('success', False),
                        'statistics': results.get('statistics', {}),
                        'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'total_duration': str(duration).split('.')[0],
                        'test_details': results.get('test_details', []),
                        'summary': results.get('summary', ''),
                        'raw_output': results.get('raw_output', '')
                    },
                    test_config=test_config
                )
                
                if chinese_report_file and log_callback:
                    log_callback(f"✅ 中文测试报告生成成功：{chinese_report_file}")
                    
            except Exception as e:
                if log_callback:
                    log_callback(f"❌ 生成中文报告失败: {e}")
            
            # 整理结果
            final_results = {
                'success': results.get('success', False),
                'message': results.get('message', '测试完成'),
                'statistics': results.get('statistics', {}),
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_duration': str(duration).split('.')[0],
                'test_details': results.get('test_details', []),
                'summary': results.get('summary', ''),
                'report_file': chinese_report_file or report_file,
                'pytest_report_file': report_file,
                'raw_output': results.get('raw_output', '')
            }
            
            if log_callback:
                log_callback(f"✅ 测试执行完成，耗时: {final_results['total_duration']}")
                
            return final_results
            
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            if log_callback:
                log_callback(f"❌ 测试执行失败: {e}")
            return {
                'success': False,
                'message': f'测试执行失败: {e}',
                'statistics': {},
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_duration': '0:00:00',
                'test_details': [],
                'summary': f'执行失败: {e}',
                'report_file': None,
                'raw_output': ''
            }
    
    def _update_test_config(self, test_config):
        """更新测试配置文件"""
        try:
            config_data = {
                'router': test_config['router'],
                'browser': {
                    'headless': test_config['browser']['headless'],
                    'browser_type': 'chromium',
                    'viewport': {'width': 1920, 'height': 1080},
                    'slow_mo': 100
                },
                'test_settings': {
                    'screenshot_on_failure': test_config['browser']['screenshot_on_failure'],
                    'video_on_failure': test_config['browser']['video_on_failure'],
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
            
            self.yaml_reader.write_yaml("config/test_config.yaml", config_data)
            self.logger.info("测试配置更新成功")
            
        except Exception as e:
            self.logger.error(f"更新配置失败: {e}")
    
    def _build_pytest_args(self, test_config):
        """构建pytest参数"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"reports/outputs/pytest_report_{timestamp}.html"
        
        # 确保报告目录存在
        os.makedirs("reports/outputs", exist_ok=True)
        
        pytest_args = [
            "-v",  # 详细输出
            "-s",  # 不捕获输出
            "--tb=short",  # 简短错误信息
            f"--html={report_file}",  # HTML报告
            "--self-contained-html",  # 自包含HTML
            "--capture=no",  # 不捕获输出
            "--maxfail=5",  # 最多失败5个就停止
            # 移除重复的日志配置
        ]
        
        # 根据测试功能选择测试文件（支持多选）
        selected_functions = test_config.get('test_function', ['全部功能'])
        if isinstance(selected_functions, str):
            selected_functions = [selected_functions]

        # 映射表
        function_file_map = {
            '登录测试': 'tests/test_login.py',
            'VLAN设置': 'tests/test_vlan.py',
            '端口映射': 'tests/test_port_mapping.py',
            'ACL规则': 'tests/test_acl.py',
            '终端分组': 'tests/test_sta_group.py'
        }

        test_files = []

        # 如果包含"全部功能"或者没有选择，则添加全部存在的测试文件
        if '全部功能' in selected_functions or not selected_functions:
            for f in function_file_map.values():
                if os.path.exists(f):
                    test_files.append(f)
        else:
            for func in selected_functions:
                file_path = function_file_map.get(func)
                if file_path and os.path.exists(file_path):
                    test_files.append(file_path)

        # 如果没有找到任何匹配文件，则抛出异常提醒
        if test_files:
            pytest_args.extend(test_files)
        else:
            raise FileNotFoundError("未找到所选功能对应的测试文件，请检查功能选择或用例文件是否存在")
        
        return pytest_args, report_file
    
    def _execute_tests(self, pytest_args, test_config, progress_callback, log_callback, result_callback, report_file):
        """执行测试"""
        cycles = test_config.get('cycles', 1)
        all_results = []
        total_stats = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
        combined_output = []
        
        for cycle in range(cycles):
            if self._stop_requested:
                break
                
            if log_callback:
                log_callback(f"🔄 开始第 {cycle + 1}/{cycles} 轮测试")
            
            if progress_callback:
                progress = int((cycle / cycles) * 90)
                progress_callback(f"执行进度: {progress}%")
            
            # 执行单轮测试
            cycle_result = self._run_single_cycle(pytest_args, cycle + 1, log_callback, result_callback)
            all_results.append(cycle_result)
            
            # 收集输出
            cycle_output = cycle_result.get('output', '')
            if cycle_output:
                combined_output.append(f"=== 第{cycle + 1}轮测试输出 ===")
                combined_output.append(cycle_output)
                combined_output.append("")
            
            # 累计统计
            cycle_stats = cycle_result.get('statistics', {})
            for key in total_stats:
                total_stats[key] += cycle_stats.get(key, 0)
        
        # 计算成功率
        if total_stats['total'] > 0:
            success_rate = (total_stats['passed'] / total_stats['total']) * 100
        else:
            success_rate = 0
        
        total_stats['success_rate'] = success_rate
        
        # 判断整体成功状态
        overall_success = total_stats['failed'] == 0 and total_stats['error'] == 0 and total_stats['total'] > 0
        
        if progress_callback:
            progress_callback("执行进度: 100%")
        
        # 检查报告文件是否生成
        if os.path.exists(report_file):
            if log_callback:
                log_callback(f"📊 pytest报告已生成: {report_file}")
        else:
            if log_callback:
                log_callback(f"⚠️ pytest报告未找到: {report_file}")
        
        return {
            'success': overall_success,
            'message': f'完成 {cycles} 轮测试，成功率 {success_rate:.1f}%',
            'statistics': total_stats,
            'test_details': all_results,
            'summary': self._generate_summary(all_results, total_stats),
            'report_file': report_file,
            'raw_output': '\n'.join(combined_output)
        }
    
    def _decode_with_fallback(self, data_bytes):
        """
        尝试多种编码方式解码字节数据
        优先尝试UTF-8，失败后尝试GBK，最后使用errors='ignore'
        """
        if not data_bytes:
            return ""
            
        # 编码尝试顺序：UTF-8 -> GBK -> CP936 -> 忽略错误的UTF-8
        encodings = ['utf-8', 'gbk', 'cp936']
        
        for encoding in encodings:
            try:
                return data_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用UTF-8并忽略错误
        try:
            return data_bytes.decode('utf-8', errors='ignore')
        except Exception:
            # 最后的保险措施
            return str(data_bytes, errors='ignore')
    
    def _run_single_cycle(self, pytest_args, cycle_num, log_callback, result_callback):
        """运行单轮测试"""
        try:
            # 使用实时输出的方式运行pytest
            cmd = [sys.executable, "-m", "pytest"] + pytest_args
            
            # 启动进程 - 使用兼容的编码处理
            self._current_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,  # 使用二进制模式，稍后手动处理编码
                bufsize=1
            )
            
            # 实时读取输出
            output_lines = []
            
            while True:
                if self._stop_requested:
                    self._current_process.terminate()
                    break
                    
                output_bytes = self._current_process.stdout.readline()
                if output_bytes == b'' and self._current_process.poll() is not None:
                    break
                    
                if output_bytes:
                    # 尝试多种编码方式解码
                    output = self._decode_with_fallback(output_bytes)
                    output = output.strip()
                    output_lines.append(output)
                    
                    if log_callback and output:
                        # 根据设置决定是否显示详细日志
                        formatted_output = self._format_log_output(output)
                        if formatted_output:
                            log_callback(formatted_output)
            
            # 等待进程完成
            return_code = self._current_process.wait() if not self._stop_requested else -1
            
            # 解析pytest输出
            all_output = '\n'.join(output_lines)
            stats = self._parse_pytest_output(all_output)
            
            # 记录结果
            if result_callback:
                result_callback({
                    'test_case': f'第{cycle_num}轮测试',
                    'status': 'PASSED' if return_code == 0 else 'FAILED',
                    'start_time': datetime.now().strftime('%H:%M:%S'),
                    'end_time': datetime.now().strftime('%H:%M:%S'),
                    'duration': '估算',
                    'message': f'退出码: {return_code}, 用例总数: {stats.get("total", 0)}'
                })
            
            if log_callback:
                if return_code == 0:
                    log_callback(f"✅ 第 {cycle_num} 轮测试成功完成")
                else:
                    log_callback(f"❌ 第 {cycle_num} 轮测试失败，退出码: {return_code}")
            
            return {
                'cycle': cycle_num,
                'returncode': return_code,
                'statistics': stats,
                'output': all_output
            }
            
        except Exception as e:
            if log_callback:
                log_callback(f"❌ 第 {cycle_num} 轮测试出错: {e}")
            return {
                'cycle': cycle_num,
                'returncode': -1,
                'statistics': {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 1},
                'output': str(e)
            }
    
    def _format_log_output(self, output):
        """格式化日志输出，添加合适的前缀"""
        # 将类似 "\u8d26\u53f7" 的转义序列转回中文，方便 GUI 显示
        def _decode_unicode_escape(s: str):
            try:
                # 先确保存在转义序列再处理，避免无意义转换
                if "\\u" in s:
                    return re.sub(r"\\u[0-9a-fA-F]{4}", lambda m: chr(int(m.group(0)[2:], 16)), s)
                return s
            except Exception:
                return s

        output = _decode_unicode_escape(output)
        # 过滤掉不重要的pytest系统信息
        skip_patterns = [
            r'cachedir:',
            r'metadata:',
            r'plugins:',
            r'rootdir:',
            r'collecting \.\.\.',
            r'platform ',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, output):
                return None
        
        # 识别页面操作日志（包含RouterTest的日志）
        if 'RouterTest' in output and 'INFO' in output:
            # 提取实际的日志内容（去掉时间戳和日志级别）
            match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} - RouterTest - INFO - (.+)', output)
            if match:
                log_content = match.group(1)
                
                # 判断是执行步骤还是页面操作日志
                if '[执行步骤]' in log_content:
                    return f"[执行步骤] {log_content.replace('[执行步骤] ', '')}"
                else:
                    # 页面操作日志
                    return f"[日志] {log_content}"
        
        # 其他重要的pytest信息
        important_patterns = [
            r'collected \d+ items',
            r'test.*::.*',
            r'\[测试开始\]',
            r'\[测试结束\]',
            r'PASSED',
            r'FAILED',
            r'ERROR',
            r'===.*===',
        ]
        
        for pattern in important_patterns:
            if re.search(pattern, output):
                return f"📝 {output}"
        
        # 如果开启了详细日志显示，则显示其他内容
        if self._show_detail_logs and output.strip():
            return f"📝 {output}"
            
        return None
    
    def _parse_pytest_output(self, output):
        """解析pytest输出获取统计信息"""
        stats = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
        
        try:
            lines = output.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 查找pytest的最终统计行
                if '=====' in line and ('passed' in line or 'failed' in line or 'error' in line):
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i + 1 < len(parts):
                            count = int(part)
                            next_part = parts[i + 1].lower()
                            
                            if 'passed' in next_part:
                                stats['passed'] = count
                            elif 'failed' in next_part:
                                stats['failed'] = count
                            elif 'skipped' in next_part:
                                stats['skipped'] = count
                            elif 'error' in next_part:
                                stats['error'] = count
                
                # 查找收集的测试数量
                elif 'collected' in line and 'item' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit() and i + 1 < len(parts) and 'item' in parts[i + 1]:
                            stats['total'] = int(part)
                            break
            
            # 如果没有找到total，计算一下
            if stats['total'] == 0:
                stats['total'] = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
            
        except Exception as e:
            self.logger.error(f"解析pytest输出失败: {e}")
        
        return stats
    
    def _generate_summary(self, all_results, total_stats):
        """生成测试摘要"""
        summary_lines = []
        
        summary_lines.append(f"📊 测试执行摘要")
        summary_lines.append(f"=" * 50)
        summary_lines.append(f"总共执行了 {len(all_results)} 轮测试")
        summary_lines.append(f"测试用例总数: {total_stats['total']}")
        summary_lines.append(f"✅ 成功: {total_stats['passed']}")
        summary_lines.append(f"❌ 失败: {total_stats['failed']}")
        summary_lines.append(f"⏭️ 跳过: {total_stats['skipped']}")
        summary_lines.append(f"💥 错误: {total_stats['error']}")
        summary_lines.append(f"📈 成功率: {total_stats.get('success_rate', 0):.1f}%")
        summary_lines.append("")
        
        # 添加每轮结果
        summary_lines.append("📋 各轮测试详情:")
        for i, result in enumerate(all_results, 1):
            returncode = result.get('returncode', -1)
            status = "✅ 成功" if returncode == 0 else "❌ 失败"
            stats = result.get('statistics', {})
            summary_lines.append(f"  第{i}轮: {status} (成功:{stats.get('passed', 0)}, 失败:{stats.get('failed', 0)})")
        
        return '\n'.join(summary_lines)
    
    def stop_tests(self):
        """停止测试"""
        self._stop_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
                self.logger.info("测试进程已终止")
            except:
                pass
        self.logger.info("收到停止测试请求")