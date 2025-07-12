# 测试执行器
import pytest
import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from utils.logger import Logger
from utils.yaml_reader import YamlReader

class TestRunner:
    """测试执行器"""
    
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.project_root = Path(__file__).parent.parent
        self._stop_requested = False
        
    def run_tests(self, test_config, progress_callback=None, log_callback=None, result_callback=None):
        """运行测试"""
        self._stop_requested = False
        start_time = datetime.now()
        
        try:
            # 更新配置文件
            self._update_test_config(test_config)
            
            # 构建pytest参数
            pytest_args = self._build_pytest_args(test_config)
            
            # 执行测试
            results = self._execute_tests(
                pytest_args, 
                test_config,
                progress_callback,
                log_callback,
                result_callback
            )
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # 整理结果
            final_results = {
                'success': results.get('success', False),
                'message': results.get('message', '测试完成'),
                'statistics': results.get('statistics', {}),
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_duration': str(duration).split('.')[0],
                'test_details': results.get('test_details', []),
                'summary': results.get('summary', '')
            }
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            return {
                'success': False,
                'message': f'测试执行失败: {e}',
                'statistics': {},
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_duration': '0:00:00',
                'test_details': [],
                'summary': f'执行失败: {e}'
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
            
        except Exception as e:
            self.logger.error(f"更新配置失败: {e}")
    
    def _build_pytest_args(self, test_config):
        """构建pytest参数"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"reports/outputs/test_report_{timestamp}.html"
        
        pytest_args = [
            "-v",  # 详细输出
            "--tb=short",  # 简短错误信息
            f"--html={report_file}",  # HTML报告
            "--self-contained-html",  # 自包含HTML
            "--capture=no",  # 不捕获输出
        ]
        
        # 根据测试功能选择测试文件
        test_function = test_config.get('test_function', '全部功能')
        
        if test_function == '登录测试':
            pytest_args.append("tests/test_login.py")
        elif test_function == 'VLAN设置':
            pytest_args.append("tests/test_vlan.py")
        elif test_function == '端口映射':
            pytest_args.append("tests/test_port_mapping.py")
        elif test_function == 'ACL规则':
            pytest_args.append("tests/test_acl.py")
        else:
            pytest_args.append("tests/")
        
        return pytest_args
    
    def _execute_tests(self, pytest_args, test_config, progress_callback, log_callback, result_callback):
        """执行测试"""
        cycles = test_config.get('cycles', 1)
        all_results = []
        total_stats = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
        
        for cycle in range(cycles):
            if self._stop_requested:
                break
                
            if log_callback:
                log_callback(f"🔄 开始第 {cycle + 1}/{cycles} 轮测试")
            
            if progress_callback:
                progress = int((cycle / cycles) * 80)  # 80% 用于测试执行
                progress_callback(f"执行进度: {progress}%")
            
            # 执行单轮测试
            cycle_result = self._run_single_cycle(pytest_args, cycle + 1, log_callback, result_callback)
            all_results.append(cycle_result)
            
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
        
        return {
            'success': overall_success,
            'message': f'完成 {cycles} 轮测试，成功率 {success_rate:.1f}%',
            'statistics': total_stats,
            'test_details': all_results,
            'summary': self._generate_summary(all_results, total_stats)
        }
    
    def _run_single_cycle(self, pytest_args, cycle_num, log_callback, result_callback):
        """运行单轮测试"""
        try:
            if log_callback:
                log_callback(f"📋 执行命令: pytest {' '.join(pytest_args)}")
            
            # 使用subprocess运行pytest，这样可以更好地控制和监控
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + pytest_args,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 解析pytest输出
            stats = self._parse_pytest_output(result.stdout, result.stderr)
            
            # 记录结果
            if result_callback:
                result_callback({
                    'test_case': f'第{cycle_num}轮测试',
                    'status': 'PASSED' if result.returncode == 0 else 'FAILED',
                    'start_time': datetime.now().strftime('%H:%M:%S'),
                    'end_time': datetime.now().strftime('%H:%M:%S'),
                    'duration': '估算',
                    'message': f'退出码: {result.returncode}'
                })
            
            if log_callback:
                if result.returncode == 0:
                    log_callback(f"✅ 第 {cycle_num} 轮测试成功")
                else:
                    log_callback(f"❌ 第 {cycle_num} 轮测试失败，退出码: {result.returncode}")
                    
                # 输出部分pytest日志
                if result.stdout:
                    lines = result.stdout.split('\n')
                    for line in lines[-10:]:  # 显示最后10行
                        if line.strip():
                            log_callback(f"📋 {line}")
            
            return {
                'cycle': cycle_num,
                'returncode': result.returncode,
                'statistics': stats,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            if log_callback:
                log_callback(f"⏰ 第 {cycle_num} 轮测试超时")
            return {
                'cycle': cycle_num,
                'returncode': -1,
                'statistics': {'total': 0, 'passed': 0, 'failed': 1, 'skipped': 0, 'error': 0},
                'stdout': '',
                'stderr': '测试超时'
            }
        except Exception as e:
            if log_callback:
                log_callback(f"❌ 第 {cycle_num} 轮测试出错: {e}")
            return {
                'cycle': cycle_num,
                'returncode': -1,
                'statistics': {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 1},
                'stdout': '',
                'stderr': str(e)
            }
    
    def _parse_pytest_output(self, stdout, stderr):
        """解析pytest输出获取统计信息"""
        stats = {'total': 0, 'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0}
        
        try:
            # 查找pytest的统计行
            lines = stdout.split('\n') + stderr.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 查找类似 "5 passed, 2 failed, 1 skipped" 的行
                if 'passed' in line or 'failed' in line or 'error' in line:
                    if '=' in line and ('passed' in line or 'failed' in line):
                        # 解析统计信息
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
            
            # 计算总数
            stats['total'] = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
            
        except Exception as e:
            self.logger.error(f"解析pytest输出失败: {e}")
        
        return stats
    
    def _generate_summary(self, all_results, total_stats):
        """生成测试摘要"""
        summary_lines = []
        
        summary_lines.append(f"总共执行了 {len(all_results)} 轮测试")
        summary_lines.append(f"测试用例总数: {total_stats['total']}")
        summary_lines.append(f"成功: {total_stats['passed']}")
        summary_lines.append(f"失败: {total_stats['failed']}")
        summary_lines.append(f"跳过: {total_stats['skipped']}")
        summary_lines.append(f"错误: {total_stats['error']}")
        summary_lines.append(f"成功率: {total_stats.get('success_rate', 0):.1f}%")
        
        # 添加每轮结果
        for i, result in enumerate(all_results, 1):
            returncode = result.get('returncode', -1)
            status = "成功" if returncode == 0 else "失败"
            summary_lines.append(f"第{i}轮: {status}")
        
        return '\n'.join(summary_lines)
    
    def stop_tests(self):
        """停止测试"""
        self._stop_requested = True
        self.logger.info("收到停止测试请求")