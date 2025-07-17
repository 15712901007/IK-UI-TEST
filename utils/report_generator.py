# 测试报告生成器 - 优化版本（修复执行时间）
from datetime import datetime
from pathlib import Path
import json
import os
import re
from jinja2 import Template
from utils.logger import Logger
from utils.yaml_reader import YamlReader

class ReportGenerator:
    """测试报告生成器 - 优化版"""
    
    def __init__(self):
        self.logger = Logger().get_logger()
        self.yaml_reader = YamlReader()
        self.report_dir = Path("reports/outputs")
        self.template_dir = Path("reports/templates")
        self.assets_dir = Path("reports/assets")
        
        # 确保目录存在
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建中文报告模板
        self._create_chinese_template()
    
    def _read_file_with_fallback(self, file_path):
        """
        尝试多种编码方式读取文件
        优先尝试UTF-8，失败后尝试GBK
        """
        encodings = ['utf-8', 'gbk', 'cp936']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                # 其他错误直接抛出
                raise e
        
        # 如果所有编码都失败，使用UTF-8并忽略错误
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"无法读取文件 {file_path}: {e}")
    
    def generate_report(self, test_results=None, test_config=None, output_dir="reports/outputs"):
        """生成测试报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.report_dir / f"中文测试报告_{timestamp}.html"
            
            # 准备报告数据
            report_data = self._prepare_report_data(test_results, test_config)
            
            # 生成HTML报告
            html_content = self._generate_html_report(report_data)
            
            # 保存报告
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"中文测试报告生成成功: {report_file}")
            return str(report_file)
            
        except Exception as e:
            self.logger.error(f"生成中文测试报告失败: {e}")
            return None
    
    def _prepare_report_data(self, test_results, test_config):
        """准备报告数据"""
        if test_results is None:
            test_results = {}
        if test_config is None:
            test_config = {}
            
        # 基本信息
        report_data = {
            'title': '路由器自动化测试报告',
            'generate_time': datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
            'test_results': test_results,
            'test_config': test_config,
            'statistics': test_results.get('statistics', {}),
            'summary': test_results.get('summary', ''),
            'success': test_results.get('success', False),
            'test_cases': self._extract_test_cases_from_output(test_results, test_config)
        }
        
        # 计算额外统计信息
        stats = report_data['statistics']
        if stats.get('total', 0) > 0:
            stats['success_rate'] = (stats.get('passed', 0) / stats['total']) * 100
        else:
            stats['success_rate'] = 0
            
        # 测试环境信息
        router_info = test_config.get('router', {})
        test_function_raw = test_config.get('test_function', '全部功能')
        if isinstance(test_function_raw, list):
            display_functions = '、'.join(test_function_raw)
        else:
            display_functions = str(test_function_raw)
        
        report_data['environment'] = {
            'router_ip': router_info.get('ip', '未知'),
            'test_version': test_config.get('test_info', {}).get('version', '1.0.0'),
            'tester': test_config.get('test_info', {}).get('tester', '自动化测试'),
            'test_environment': test_config.get('test_info', {}).get('environment', '测试环境'),
            'browser_mode': '无头模式' if test_config.get('browser', {}).get('headless', False) else '可视模式',
            'test_cycles': test_config.get('cycles', 1),
            'test_function': display_functions,
            'start_time': test_results.get('start_time', '未知'),
            'end_time': test_results.get('end_time', '未知'),
            'total_duration': test_results.get('total_duration', '未知')
        }
        
        self.logger.info(f"报告数据准备完成，测试用例数量: {len(report_data['test_cases'])}")
        return report_data

    def _extract_test_cases_from_output(self, test_results, test_config):
        """从原始输出中提取测试用例详情"""
        test_cases = []
        
        # 获取原始输出
        raw_output = test_results.get('raw_output', '')
        if not raw_output:
            # 尝试从test_details中获取
            test_details = test_results.get('test_details', [])
            if test_details:
                raw_output = '\n'.join([detail.get('output', '') for detail in test_details])
        
        if not raw_output:
            self.logger.warning("没有找到测试输出数据")
            return self._create_fallback_test_cases(test_results, test_config)
        
        # 加载VLAN配置
        yaml_config = self._load_vlan_yaml_config()
        
        # 加载登录测试数据（用于参数化用例描述）
        login_config = self._load_login_yaml_config()
        
        # 解析测试用例
        test_cases = self._parse_test_cases_from_output(raw_output, yaml_config, login_config)
        
        if not test_cases:
            self.logger.warning("从输出中未解析到测试用例，使用备用方案")
            test_cases = self._create_fallback_test_cases(test_results, test_config)
        
        return test_cases

    def _load_vlan_yaml_config(self):
        """加载VLAN YAML配置"""
        try:
            vlan_config = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            self.logger.info(f"成功加载VLAN配置，包含 {len(vlan_config.get('test_cases', {}))} 个测试用例")
            return vlan_config
        except Exception as e:
            self.logger.error(f"加载VLAN配置失败: {e}")
            return {}

    def _load_login_yaml_config(self):
        """加载登录 YAML 测试数据"""
        try:
            cfg = self.yaml_reader.read_yaml("data/login_data.yaml")
            return cfg or {}
        except Exception as e:
            self.logger.error(f"加载登录测试数据失败: {e}")
            return {}

    def _parse_test_cases_from_output(self, raw_output, vlan_yaml_config, login_yaml_config):
        """从原始输出解析测试用例"""
        test_cases = []
        lines = raw_output.split('\n')
        
        current_test_case = None
        current_execution_details = []
        
        self.logger.info(f"开始解析测试输出，共 {len(lines)} 行")
        
        for line in lines:
            line = line.strip()
            
            # 检测测试用例开始
            if '[测试开始]' in line:
                # 保存前一个测试用例
                if current_test_case:
                    current_test_case['execution_details'] = self._clean_execution_details(current_execution_details)
                    current_test_case['execution_summary'] = self._create_execution_summary(current_execution_details)
                    if current_test_case['status'] == 'RUNNING':
                        current_test_case['status'] = 'PASSED'
                    test_cases.append(current_test_case)
                
                # 提取测试方法名及参数（支持参数化用例）
                # 例如: [测试开始] test_invalid_login (admin/wrong_password)
                test_match = re.search(r'\[测试开始\]\s+(\w+)(?:\s*\((.*?)\))?', line)
                if test_match:
                    method_name = test_match.group(1)
                    param_desc = test_match.group(2)  # 可能为空

                    # 根据常见方法名映射更友好的中文名称
                    default_name_map = {
                        'test_valid_login': '有效登录功能测试',
                        'test_invalid_login': '无效登录功能测试'
                    }

                    default_name = default_name_map.get(method_name, f'{method_name} 功能测试')

                    # 始终保持中文描述；参数化信息只用于 method_name，不影响 name
                    display_name = default_name
                    
                    # 从YAML配置获取测试用例信息
                    yaml_test_case = vlan_yaml_config.get('test_cases', {}).get(method_name, {})
                    
                    # 若为参数化登录场景，尝试从 login_yaml_config 匹配 description
                    if method_name == 'test_invalid_login' and param_desc:
                        parts = param_desc.split('/') if param_desc else []
                        user = parts[0] if len(parts) > 0 else ''
                        pwd = parts[1] if len(parts) > 1 else ''
                        for case in login_yaml_config.get('invalid_login', []):
                            if str(case.get('username')) == user and str(case.get('password')) == pwd:
                                display_name = case.get('description', display_name)
                                break
                    elif method_name == 'test_valid_login':
                        # 取有效登录描述
                        first_valid = login_yaml_config.get('valid_login', [{}])[0]
                        display_name = first_valid.get('description', display_name)

                    # 依据方法名判断测试模块
                    if 'login' in method_name.lower():
                        test_class = 'LOGIN_TEST'
                    else:
                        test_class = 'VLAN_TEST'
                    
                    current_test_case = {
                        'case_id': len(test_cases) + 1,
                        'test_class': test_class,
                        'method_name': method_name + (f"[{param_desc}]" if param_desc else ""),
                        'name': yaml_test_case.get('name', display_name),
                        'business_scenario': yaml_test_case.get('business_scenario', '验证功能正确性'),
                        'test_steps': yaml_test_case.get('test_steps', ['1. 执行测试准备', '2. 执行核心操作', '3. 验证结果']),
                        'risk_level': yaml_test_case.get('risk_level', '中等'),
                        'priority': yaml_test_case.get('priority', '中'),
                        'status': 'RUNNING',
                        'execution_details': [],
                        'start_time': self._extract_timestamp_from_line(line),
                        'duration': '计算中...'
                    }
                    current_execution_details = []
                    self.logger.info(f"发现测试用例: {current_test_case['method_name']}")
            
            # 收集执行详情（过滤重复）
            if current_test_case:
                # 只收集 [执行步骤] 的日志，过滤重复信息
                if '[执行步骤]' in line:
                    step_content = line.split('[执行步骤]')[-1].strip()
                    timestamp = self._extract_timestamp_from_line(line)
                    
                    # 避免重复记录
                    if not any(detail.get('content') == step_content for detail in current_execution_details):
                        current_execution_details.append({
                            'type': 'step',
                            'timestamp': timestamp,
                            'content': step_content
                        })
                
                # 收集重要的系统日志（但过滤重复）
                elif 'RouterTest - INFO -' in line and '[执行步骤]' not in line:
                    log_content = line.split('RouterTest - INFO -')[-1].strip()
                    timestamp = self._extract_timestamp_from_line(line)
                    
                    # 只记录重要的系统操作
                    if any(keyword in log_content for keyword in ['成功', '开始添加', '添加完成', '获取到VLAN']):
                        if not any(detail.get('content') == log_content for detail in current_execution_details):
                            current_execution_details.append({
                                'type': 'system',
                                'timestamp': timestamp,
                                'content': log_content
                            })
            
            # 检测测试结果和时间
            if current_test_case:
                if '[测试结束]' in line:
                    current_test_case['end_time'] = self._extract_timestamp_from_line(line)
                    current_test_case['duration'] = self._calculate_duration_from_log(current_execution_details)
                    
                    if '成功' in line:
                        current_test_case['status'] = 'PASSED'
                    elif '失败' in line:
                        current_test_case['status'] = 'FAILED'
                elif 'PASSED' in line and current_test_case['status'] == 'RUNNING':
                    current_test_case['status'] = 'PASSED'
                elif 'FAILED' in line and current_test_case['status'] == 'RUNNING':
                    current_test_case['status'] = 'FAILED'
                elif 'ERROR' in line and 'RouterTest' not in line and current_test_case['status'] == 'RUNNING':
                    # 仅当pytest自身报ERROR时才标记，为避免RouterTest自定义ERROR日志误判
                    current_test_case['status'] = 'ERROR'
        
        # 添加最后一个测试用例
        if current_test_case:
            current_test_case['execution_details'] = self._clean_execution_details(current_execution_details)
            current_test_case['execution_summary'] = self._create_execution_summary(current_execution_details)
            if current_test_case['status'] == 'RUNNING':
                current_test_case['status'] = 'PASSED'
            test_cases.append(current_test_case)
        
        self.logger.info(f"成功解析出 {len(test_cases)} 个测试用例")
        return test_cases

    def _clean_execution_details(self, execution_details):
        """清理执行详情，去除重复和无用信息"""
        cleaned_details = []
        seen_contents = set()
        
        for detail in execution_details:
            content = detail.get('content', '')
            
            # 跳过重复内容
            if content in seen_contents:
                continue
            
            # 跳过无用信息
            if any(skip_word in content for skip_word in ['setup_method', '调试', 'caplog']):
                continue
            
            seen_contents.add(content)
            cleaned_details.append(detail)
        
        return cleaned_details

    def _calculate_duration_from_log(self, execution_details):
        """从执行详情中计算持续时间"""
        # 查找执行耗时信息
        for detail in execution_details:
            content = detail.get('content', '')
            if '执行耗时:' in content:
                duration_match = re.search(r'执行耗时:\s*([\d.]+)秒', content)
                if duration_match:
                    return f"{duration_match.group(1)}秒"
        
        # 如果没有找到，尝试从时间戳计算
        if len(execution_details) >= 2:
            start_time = execution_details[0].get('timestamp', '')
            end_time = execution_details[-1].get('timestamp', '')
            
            if start_time != '未知' and end_time != '未知':
                try:
                    from datetime import datetime
                    start = datetime.strptime(start_time, '%H:%M:%S')
                    end = datetime.strptime(end_time, '%H:%M:%S')
                    duration = end - start
                    return f"{duration.total_seconds():.1f}秒"
                except:
                    pass
        
        return '未知'

    def _create_execution_summary(self, execution_details):
        """创建执行摘要"""
        total_steps = len([d for d in execution_details if d['type'] == 'step'])
        total_actions = len([d for d in execution_details if d['type'] == 'system'])
        
        # 提取关键步骤
        key_steps = []
        for detail in execution_details:
            if detail['type'] == 'step':
                content = detail['content']
                if any(keyword in content for keyword in ['开始执行', '创建成功', '创建失败', '完成', '执行耗时']):
                    key_steps.append(f"{detail['timestamp']}: {content}")
        
        return {
            'total_steps': total_steps,
            'total_actions': total_actions,
            'key_steps': key_steps[:5]  # 只显示前5个关键步骤
        }

    def _extract_timestamp_from_line(self, line):
        """从日志行提取时间戳"""
        # 尝试提取时分秒格式
        timestamp_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line)
        if timestamp_match:
            return timestamp_match.group(1)
        
        # 尝试提取完整时间戳格式
        full_timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if full_timestamp_match:
            return full_timestamp_match.group(1).split()[-1]  # 只返回时间部分
        
        return '未知'

    def _create_fallback_test_cases(self, test_results, test_config):
        """创建备用测试用例"""
        test_cases = []
        stats = test_results.get('statistics', {})
        yaml_config = self._load_vlan_yaml_config()
        yaml_test_cases = yaml_config.get('test_cases', {})
        
        total = stats.get('total', 0)
        passed = stats.get('passed', 0)
        failed = stats.get('failed', 0)
        
        case_count = 0
        for method_name, case_config in yaml_test_cases.items():
            if case_count >= total:
                break
                
            # 分配状态
            if case_count < passed:
                status = 'PASSED'
                duration = '2-5秒'
            elif case_count < passed + failed:
                status = 'FAILED'
                duration = '1-3秒'
            else:
                status = 'ERROR'
                duration = '未知'
            
            test_cases.append({
                'case_id': case_count + 1,
                'test_class': 'LOGIN_TEST' if 'login' in method_name.lower() else 'VLAN_TEST',
                'method_name': method_name,
                'name': '有效登录功能测试' if method_name == 'test_valid_login' else ('无效登录功能测试' if 'invalid_login' in method_name else f'{method_name} 功能测试'),
                'business_scenario': case_config.get('business_scenario', '验证功能正确性'),
                'test_steps': case_config.get('test_steps', ['1. 执行测试准备', '2. 执行核心操作', '3. 验证结果']),
                'risk_level': case_config.get('risk_level', '中等'),
                'priority': case_config.get('priority', '中'),
                'status': status,
                'start_time': '未知',
                'end_time': '未知',
                'duration': duration,
                'execution_details': [
                    {
                        'type': 'step',
                        'timestamp': '未知',
                        'content': f'备用方案生成的 {status} 测试用例'
                    }
                ],
                'execution_summary': {
                    'total_steps': 1,
                    'total_actions': 0,
                    'key_steps': [f'备用方案: {status} 测试用例']
                }
            })
            case_count += 1
        
        return test_cases
    
    def _generate_html_report(self, report_data):
        """生成HTML报告"""
        template_content = self._get_chinese_template()
        template = Template(template_content)
        
        return template.render(**report_data)
    
    def _create_chinese_template(self):
        """创建中文报告模板"""
        template_file = self.template_dir / "chinese_report_template.html"
        
        # 强制重新创建模板
        template_content = self._get_table_style_template()
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(template_content)
            self.logger.info("强制重新创建表格样式模板成功")
        except Exception as e:
            self.logger.error(f"创建中文报告模板失败: {e}")
    
    def _get_table_style_template(self):
        """获取表格样式模板"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Microsoft YaHei', Arial, sans-serif; 
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container { 
            max-width: 1600px; 
            margin: 0 auto; 
            padding: 20px;
        }
        
        .header { 
            background: linear-gradient(135deg, #4CAF50, #45a049);
            color: white; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        
        .summary-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #4CAF50;
        }
        
        .summary-card.failed { border-left-color: #f44336; }
        .summary-card.total { border-left-color: #2196F3; }
        .summary-card.rate { border-left-color: #FF9800; }
        
        .card-title { font-size: 0.9em; color: #666; margin-bottom: 5px; }
        .card-value { font-size: 2em; font-weight: bold; }
        .card-value.success { color: #4CAF50; }
        .card-value.error { color: #f44336; }
        .card-value.info { color: #2196F3; }
        .card-value.warning { color: #FF9800; }
        
        .test-info-section {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #4CAF50;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 10px 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #4CAF50;
        }
        
        .info-label { font-weight: bold; color: #555; }
        .info-value { color: #333; }
        
        .test-table-section {
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .table-header {
            background: #4CAF50;
            color: white;
            padding: 15px 20px;
            font-size: 1.3em;
            font-weight: bold;
        }
        
        .test-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }
        
        .test-table thead {
            background: #45a049;
            color: white;
        }
        
        .test-table th,
        .test-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .test-table th {
            font-weight: bold;
            position: sticky;
            top: 0;
        }
        
        .test-table tbody tr:hover {
            background-color: #f5f5f5;
        }
        
        .test-table tbody tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        
        .status-badge {
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: bold;
            color: white;
            display: inline-block;
        }
        
        .status-badge.passed { background: #4CAF50; }
        .status-badge.failed { background: #f44336; }
        .status-badge.error { background: #FF9800; }
        
        .details-btn {
            background: #2196F3;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
        }
        
        .details-btn:hover {
            background: #1976D2;
        }
        
        .details-modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }
        
        .modal-content {
            background-color: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 10px;
            width: 90%;
            max-width: 1200px;
            max-height: 80vh;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .modal-header {
            background: #4CAF50;
            color: white;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-title { font-size: 1.3em; font-weight: bold; }
        
        .close-btn {
            background: none;
            border: none;
            color: white;
            font-size: 1.5em;
            cursor: pointer;
        }
        
        .modal-body {
            padding: 20px;
            max-height: 60vh;
            overflow-y: auto;
        }
        
        .detail-section {
            margin-bottom: 25px;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }
        
        .detail-title {
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
            font-size: 1.1em;
        }
        
        .steps-list {
            list-style: none;
            padding: 0;
        }
        
        .steps-list li {
            padding: 8px 12px;
            margin: 5px 0;
            background: #f8f9fa;
            border-left: 3px solid #4CAF50;
            border-radius: 4px;
        }
        
        .execution-timeline {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        
        .timeline-item {
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .timeline-item:last-child { border-bottom: none; }
        
        .timeline-item.step { background: #e8f5e8; }
        .timeline-item.system { background: #e3f2fd; }
        .timeline-item.error { background: #ffebee; }
        
        .timeline-time {
            font-size: 0.8em;
            color: #666;
            min-width: 70px;
        }
        
        .timeline-content { flex: 1; }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .test-table { font-size: 0.8em; }
            .test-table th,
            .test-table td { padding: 8px 10px; }
            .modal-content { margin: 2% auto; width: 95%; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 报告头部 -->
        <div class="header">
            <h1>🤖 {{ title }}</h1>
            <div>报告生成时间：{{ generate_time }}</div>
            <div style="margin-top: 10px;">
                {% if success %}
                <span style="background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px;">
                    ✅ 测试通过
                </span>
                {% else %}
                <span style="background: rgba(255,255,255,0.2); padding: 8px 20px; border-radius: 20px;">
                    ❌ 测试失败
                </span>
                {% endif %}
            </div>
        </div>

        <!-- 测试摘要 -->
        <div class="summary-section">
            <div class="section-title">📊 测试摘要</div>
            <div class="summary-cards">
                <div class="summary-card total">
                    <div class="card-title">测试用例总数</div>
                    <div class="card-value info">{{ statistics.total or 0 }}</div>
                </div>
                <div class="summary-card">
                    <div class="card-title">成功用例</div>
                    <div class="card-value success">{{ statistics.passed or 0 }}</div>
                </div>
                <div class="summary-card failed">
                    <div class="card-title">失败用例</div>
                    <div class="card-value error">{{ statistics.failed or 0 }}</div>
                </div>
                <div class="summary-card rate">
                    <div class="card-title">成功率</div>
                    <div class="card-value warning">{{ "%.1f"|format(statistics.success_rate or 0) }}%</div>
                </div>
            </div>
        </div>

        <!-- 测试环境信息 -->
        <div class="test-info-section">
            <div class="section-title">🌐 测试环境信息</div>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">🔗 路由器IP：</span>
                    <span class="info-value">{{ environment.router_ip }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🧪 测试功能：</span>
                    <span class="info-value">{{ environment.test_function }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">👤 测试人员：</span>
                    <span class="info-value">{{ environment.tester }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">🔄 循环次数：</span>
                    <span class="info-value">{{ environment.test_cycles }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">⏰ 开始时间：</span>
                    <span class="info-value">{{ environment.start_time }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">⏰ 结束时间：</span>
                    <span class="info-value">{{ environment.end_time }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">⏱️ 总耗时：</span>
                    <span class="info-value">{{ environment.total_duration }}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">📋 测试版本：</span>
                    <span class="info-value">{{ environment.test_version }}</span>
                </div>
            </div>
        </div>

        <!-- 详细测试用例表格 -->
        <div class="test-table-section">
            <div class="table-header">📝 详细信息 ({{ test_cases|length }} 个测试用例)</div>
            <table class="test-table">
                <thead>
                    <tr>
                        <th>编号</th>
                        <th>测试类</th>
                        <th>测试方法</th>
                        <th>用例描述</th>
                        <th>执行时间</th>
                        <th>执行结果</th>
                        <th>详细信息</th>
                    </tr>
                </thead>
                <tbody>
                    {% for test_case in test_cases %}
                    <tr>
                        <td>{{ test_case.case_id }}</td>
                        <td>{{ test_case.test_class }}</td>
                        <td>{{ test_case.method_name }}</td>
                        <td>{{ test_case.name }}</td>
                        <td>{{ test_case.duration or '未知' }}</td>
                        <td>
                            {% if test_case.status == 'PASSED' %}
                            <span class="status-badge passed">成功</span>
                            {% elif test_case.status == 'FAILED' %}
                            <span class="status-badge failed">失败</span>
                            {% else %}
                            <span class="status-badge error">错误</span>
                            {% endif %}
                        </td>
                        <td>
                            <button class="details-btn" onclick="showDetails({{ loop.index0 }})">
                                查看详情
                            </button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- 详情模态框 -->
        <div id="detailsModal" class="details-modal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title" id="modalTitle">测试用例详情</div>
                    <button class="close-btn" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body" id="modalBody">
                    <!-- 详情内容将在这里动态加载 -->
                </div>
            </div>
        </div>

    </div>

    <script>
        // 测试用例数据
        const testCases = {{ test_cases|tojson }};
        
        function showDetails(index) {
            const testCase = testCases[index];
            const modal = document.getElementById('detailsModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');
            
            modalTitle.textContent = testCase.name;
            
            let detailsHtml = `
                <div class="detail-section">
                    <div class="detail-title">💼 业务场景</div>
                    <div>${testCase.business_scenario}</div>
                </div>
                
                <div class="detail-section">
                    <div class="detail-title">📋 预定义测试步骤</div>
                    <ul class="steps-list">
                        ${testCase.test_steps.map(step => `<li>${step}</li>`).join('')}
                    </ul>
                </div>
                
                <div class="detail-section">
                    <div class="detail-title">🚀 实际执行详情</div>
                    <div class="execution-timeline">
                        ${testCase.execution_details.map(detail => `
                            <div class="timeline-item ${detail.type}">
                                <div class="timeline-time">${detail.timestamp}</div>
                                <div class="timeline-content">${detail.content}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="detail-section">
                    <div class="detail-title">📊 执行摘要</div>
                    <div>
                        <strong>执行步骤数：</strong>${testCase.execution_summary ? testCase.execution_summary.total_steps : 0}<br>
                        <strong>系统操作数：</strong>${testCase.execution_summary ? testCase.execution_summary.total_actions : 0}<br>
                        <strong>执行时间：</strong>${testCase.duration}
                    </div>
                </div>
            `;
            
            modalBody.innerHTML = detailsHtml;
            modal.style.display = 'block';
        }
        
        function closeModal() {
            document.getElementById('detailsModal').style.display = 'none';
        }
        
        // 点击模态框外部关闭
        window.onclick = function(event) {
            const modal = document.getElementById('detailsModal');
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        }
        
        // ESC键关闭模态框
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>'''
    
    def _get_chinese_template(self):
        """获取中文模板内容"""
        # 强制使用新模板
        return self._get_table_style_template()