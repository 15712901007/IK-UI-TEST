# VLAN功能测试 - 优化版本（完全基于YAML配置）
import pytest
import sys
import os
from pathlib import Path
import time
import json
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pages.vlan_page import VlanPage
from utils.yaml_reader import YamlReader
from utils.logger import Logger
from utils.constants import DOWNLOAD_DIR

class TestVlan:
    """VLAN功能测试类 - 完全基于YAML配置的优化版本"""
    
    def setup_method(self):
        """测试前准备"""
        self.yaml_reader = YamlReader()
        self.logger = Logger().get_logger()
        
        # 加载VLAN测试数据
        try:
            self.vlan_data = self.yaml_reader.read_yaml("data/vlan_data.yaml")
            if not self.vlan_data:
                raise Exception("VLAN测试数据为空")
        except Exception as e:
            self.logger.error(f"加载VLAN测试数据失败: {str(e)}")
            pytest.fail(f"无法加载测试数据: {str(e)}")
        
        # 存储执行详情
        self.execution_details = []
        self.test_start_time = None
        
    def _log_step(self, step_info, step_type="step"):
        """记录执行步骤 - 优化版（减少重复输出）"""
        timestamp = time.strftime('%H:%M:%S')
        
        # 存储到实例变量
        self.execution_details.append({
            'timestamp': timestamp,
            'step': step_info,
            'type': step_type
        })
        
        # 只使用一种日志记录方式，避免重复
        self.logger.info(f"[执行步骤] {step_info}")
        
    def test_add_vlan(self, logged_in_page, caplog):
        """测试添加VLAN - 完全基于YAML配置"""
        self.test_start_time = time.time()
        print("[测试开始] test_add_vlan", flush=True)
        
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        
        with caplog.at_level(logging.INFO):
            try:
                # 从YAML获取测试用例配置
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_add_vlan', {})
                basic_vlans = self.vlan_data.get('basic_vlans', [])
                
                if not basic_vlans:
                    pytest.fail("未找到基础VLAN测试数据")
                
                vlan_config = basic_vlans[0]  # 使用第一个基础VLAN配置
                
                self._log_step("测试初始化完成")
                self._log_step(f"开始执行: {test_case_config.get('name', 'VLAN添加测试')}")
                self._log_step(f"业务场景: {test_case_config.get('business_scenario', '验证VLAN创建功能')}")
                
                # 记录YAML中定义的测试步骤
                test_steps = test_case_config.get('test_steps', [])
                for i, step in enumerate(test_steps, 1):
                    self._log_step(f"预定义步骤{i}: {step}")
                
                self._log_step(f"使用测试数据: ID={vlan_config.get('id')}, Name={vlan_config.get('name')}")
                
                # 创建VLAN页面对象
                vlan_page = VlanPage(logged_in_page)
                
                # 开始执行VLAN创建
                self._log_step("开始执行VLAN创建操作")
                
                result = vlan_page.add_vlan(
                    vlan_id=vlan_config.get('id'),
                    vlan_name=vlan_config.get('name'),
                    ip_addr=vlan_config.get('ip_addr'),
                    comment=vlan_config.get('comment')
                )
                
                if result:
                    self._log_step(f"VLAN {vlan_config.get('name')} 创建成功", "success")
                else:
                    self._log_step(f"VLAN {vlan_config.get('name')} 创建失败", "error")
                    
                self._log_step("测试执行完成")
                
                # 计算执行时间
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                
                print(f"[测试结束] test_add_vlan - {'成功' if result else '失败'}", flush=True)
                assert result == True, f"VLAN {vlan_config.get('name')} 添加应该成功"
                
            except Exception as e:
                self._log_step(f"测试执行异常: {str(e)}", "error")
                print(f"[测试异常] test_add_vlan: {str(e)}", flush=True)
                raise
        
    def test_add_multiple_vlans(self, logged_in_page, caplog):
        """测试添加多个VLAN - 完全基于YAML配置"""
        self.test_start_time = time.time()
        print("[测试开始] test_add_multiple_vlans", flush=True)
        
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        
        with caplog.at_level(logging.INFO):
            try:
                # 从YAML获取测试用例配置
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_add_multiple_vlans', {})
                batch_vlans = self.vlan_data.get('batch_vlans', [])
                
                if not batch_vlans:
                    pytest.fail("未找到批量VLAN测试数据")
                
                self._log_step("批量测试初始化完成")
                self._log_step(f"开始执行: {test_case_config.get('name', '批量VLAN添加测试')}")
                self._log_step(f"业务场景: {test_case_config.get('business_scenario', '验证批量VLAN创建功能')}")
                self._log_step(f"准备批量创建 {len(batch_vlans)} 个VLAN")
                
                # 记录YAML中定义的测试步骤
                test_steps = test_case_config.get('test_steps', [])
                for i, step in enumerate(test_steps, 1):
                    self._log_step(f"预定义步骤{i}: {step}")
                
                vlan_page = VlanPage(logged_in_page)
                success_count = 0
                
                for i, vlan in enumerate(batch_vlans, 1):
                    self._log_step(f"正在创建第{i}个VLAN: {vlan['name']}")
                    
                    try:
                        result = vlan_page.add_vlan(
                            vlan_id=vlan["id"],
                            vlan_name=vlan["name"], 
                            ip_addr=vlan["ip_addr"],
                            comment=vlan["comment"]
                        )
                        
                        if result:
                            success_count += 1
                            self._log_step(f"VLAN {vlan['name']} 创建成功", "success")
                        else:
                            self._log_step(f"VLAN {vlan['name']} 创建失败", "error")
                    except Exception as e:
                        self._log_step(f"VLAN {vlan['name']} 创建异常: {str(e)}", "error")
                    
                    # 添加间隔避免操作过快
                    time.sleep(1)
                
                self._log_step(f"批量创建完成，成功率: {success_count}/{len(batch_vlans)}")
                self._log_step("批量测试执行完成")
                
                # 计算执行时间
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                
                print(f"[测试结束] test_add_multiple_vlans - 成功{success_count}/{len(batch_vlans)}", flush=True)
                assert success_count > 0, f"至少应该成功添加一个VLAN，实际成功: {success_count}"
                
            except Exception as e:
                self._log_step(f"批量测试执行异常: {str(e)}", "error")
                print(f"[测试异常] test_add_multiple_vlans: {str(e)}", flush=True)
                raise
        
    def test_get_vlan_list(self, logged_in_page, caplog):
        """测试获取VLAN列表 - 完全基于YAML配置"""
        self.test_start_time = time.time()
        print("[测试开始] test_get_vlan_list", flush=True)
        
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        
        with caplog.at_level(logging.INFO):
            try:
                # 从YAML获取测试用例配置
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_get_vlan_list', {})
                
                self._log_step("VLAN列表查询测试初始化完成")
                self._log_step(f"开始执行: {test_case_config.get('name', 'VLAN列表查询测试')}")
                self._log_step(f"业务场景: {test_case_config.get('business_scenario', '验证VLAN列表查询功能')}")
                
                # 记录YAML中定义的测试步骤
                test_steps = test_case_config.get('test_steps', [])
                for i, step in enumerate(test_steps, 1):
                    self._log_step(f"预定义步骤{i}: {step}")
                    
                vlan_page = VlanPage(logged_in_page)
                
                self._log_step("开始获取VLAN列表")
                vlan_list = vlan_page.get_vlan_list()
                
                self._log_step(f"成功获取VLAN列表，共 {len(vlan_list)} 条记录")
                
                # 只显示前3个VLAN信息，避免冗长输出
                for i, vlan in enumerate(vlan_list[:3], 1):
                    self._log_step(f"VLAN记录{i}: ID={vlan.get('id', '?')}, Name={vlan.get('name', '?')}")
                    
                if len(vlan_list) > 3:
                    self._log_step(f"还有 {len(vlan_list) - 3} 个VLAN记录未显示")
                    
                self._log_step("VLAN列表查询测试完成")
                
                # 计算执行时间
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                
                print(f"[测试结束] test_get_vlan_list - 成功获取{len(vlan_list)}条记录", flush=True)
                assert isinstance(vlan_list, list), "VLAN列表应该是一个列表"
                
            except Exception as e:
                self._log_step(f"VLAN列表查询测试异常: {str(e)}", "error")
                print(f"[测试异常] test_get_vlan_list: {str(e)}", flush=True)
                raise
        
    def test_vlan_workflow(self, logged_in_page, caplog):
        """测试完整的VLAN工作流程 - 修正扩展IP添加顺序"""
        self.test_start_time = time.time()
        print("[测试开始] test_vlan_workflow", flush=True)

        if logged_in_page is None:
            pytest.skip("Playwright 不可用")

        with caplog.at_level(logging.INFO):
            try:
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_vlan_workflow', {})
                workflow_vlans = self.vlan_data.get('workflow_vlans', [])

                if not workflow_vlans:
                    pytest.fail("未找到工作流程测试VLAN数据")

                self._log_step("VLAN工作流程测试初始化完成")
                self._log_step(f"开始执行: {test_case_config.get('name', 'VLAN工作流程测试')}")
                self._log_step(f"业务场景: {test_case_config.get('business_scenario', '验证VLAN完整工作流程')}")

                vlan_page = VlanPage(logged_in_page)

                # 1. 获取当前VLAN状态
                self._log_step("步骤1: 查看当前系统VLAN配置状态")
                try:
                    initial_list = vlan_page.get_vlan_list()
                    initial_count = len(initial_list)
                    self._log_step(f"当前系统中有 {initial_count} 个VLAN")
                except Exception as e:
                    self._log_step(f"获取VLAN列表异常: {str(e)}", "error")
                    initial_count = 0

                # 2. 准备测试VLAN配置
                self._log_step("步骤2: 规划新VLAN配置")
                test_vlan = workflow_vlans[0]
                self._log_step(f"计划创建VLAN: ID={test_vlan['id']}, Name={test_vlan['name']}")

                # 3. 手动分步填写表单并添加扩展IP
                self._log_step("步骤3: 执行新VLAN创建操作（含扩展IP）")
                assert vlan_page.navigate_to_vlan_page(), "导航到VLAN页面失败"
                assert vlan_page.click_link_by_text(vlan_page.add_link), "点击添加按钮失败"
                time.sleep(2)
                assert vlan_page.input_text(vlan_page.vlan_id_input, test_vlan["id"]), "输入VLAN ID失败"
                assert vlan_page.input_text(vlan_page.vlan_name_input, test_vlan["name"]), "输入VLAN名称失败"
                assert vlan_page.input_text(vlan_page.ip_addr_input, test_vlan["ip_addr"]), "输入IP地址失败"
                if test_vlan.get("comment"):
                    vlan_page.input_text(vlan_page.comment_input, test_vlan["comment"])

                # 先添加扩展IP
                extend_ips = test_vlan.get('extend_ips', [])
                for ext in extend_ips:
                    ip = ext.get('ip')
                    mask = ext.get('mask')
                    self._log_step(f"添加扩展IP {ip} {mask if mask else ''}")
                    extend_ip_result = vlan_page.add_extend_ip(ip, mask)
                    assert extend_ip_result, f"扩展IP {ip} 添加操作未成功执行"
                    self._log_step(f"扩展IP添加操作{'成功' if extend_ip_result else '失败'}", "success" if extend_ip_result else "error")
                    assert vlan_page.is_extend_ip_in_table(ip), f"扩展IP {ip} 未出现在表格中"
                    self._log_step(f"扩展IP {ip} 已出现在表格中", "success")

                # 最后点击保存
                assert vlan_page.click_by_role(vlan_page.save_button_role[0], vlan_page.save_button_role[1]), "点击保存按钮失败"
                time.sleep(3)
                vlan_page.page.wait_for_load_state("networkidle", timeout=10000)
                self._log_step("点击保存按钮完成", "success")

                # 5. 验证VLAN配置结果
                self._log_step("步骤4: 验证VLAN配置结果")
                vlan_list = vlan_page.get_vlan_list()
                assert any(v.get('id') == test_vlan['id'] for v in vlan_list), "新VLAN未出现在列表中"
                self._log_step("VLAN配置验证通过", "success")

                self._log_step("VLAN工作流程测试完成")
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                print(f"[测试结束] test_vlan_workflow - 成功", flush=True)

            except Exception as e:
                self._log_step(f"工作流程测试执行异常: {str(e)}", "error")
                print(f"[测试异常] test_vlan_workflow: {str(e)}", flush=True)
                raise
    
    def test_add_vlan_required_fields(self, logged_in_page, caplog):
        """VLAN必填项校验测试 - 校验ID和名称为空时的提示"""
        self.test_start_time = time.time()
        print("[测试开始] test_add_vlan_required_fields", flush=True)
        
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        
        with caplog.at_level(logging.INFO):
            try:
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_add_vlan_required_fields', {})
                invalid_vlans = self.vlan_data.get('invalid_vlans', [])
                vlan_page = VlanPage(logged_in_page)
                # 校验ID为空
                vlan_no_id = invalid_vlans[0]
                self._log_step("【异常场景】ID为空，尝试保存")
                vlan_page.add_vlan_with_partial_fields(
                    vlan_id=vlan_no_id['id'],
                    vlan_name=vlan_no_id['name'],
                    ip_addr=vlan_no_id['ip_addr'],
                    comment=vlan_no_id['comment']
                )
                assert vlan_page.get_required_field_message('vlanID 字段必填'), "未检测到vlanID必填提示"
                self._log_step('断言页面出现"vlanID 字段必填"提示', "success")
                # 校验名称为空
                vlan_no_name = invalid_vlans[1]
                self._log_step("【异常场景】名称为空，尝试保存")
                vlan_page.add_vlan_with_partial_fields(
                    vlan_id=vlan_no_name['id'],
                    vlan_name=vlan_no_name['name'],
                    ip_addr=vlan_no_name['ip_addr'],
                    comment=vlan_no_name['comment']
                )
                assert vlan_page.get_required_field_message('vlan名称 字段必填'), "未检测到vlan名称必填提示"
                self._log_step('断言页面出现"vlan名称 字段必填"提示', "success")
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                print("[测试结束] test_add_vlan_required_fields", flush=True)
            except Exception as e:
                self._log_step(f"必填项校验测试异常: {str(e)}", "error")
                print(f"[测试异常] test_add_vlan_required_fields: {str(e)}", flush=True)
                raise
    
    def test_add_vlan_invalid_fields(self, logged_in_page, caplog):
        """VLAN字段格式校验测试 - 校验ID超范围、名称不规范、IP不规范时的提示"""
        self.test_start_time = time.time()
        print("[测试开始] test_add_vlan_invalid_fields", flush=True)
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        with caplog.at_level(logging.INFO):
            try:
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_add_vlan_invalid_fields', {})
                invalid_vlans = self.vlan_data.get('invalid_vlans', [])
                vlan_page = VlanPage(logged_in_page)
                # 校验ID超范围
                vlan_id_out_of_range = next((v for v in invalid_vlans if v['id'] == '9999'), None)
                self._log_step("【异常场景】ID超范围，尝试保存")
                vlan_page.add_vlan_with_partial_fields(
                    vlan_id=vlan_id_out_of_range['id'],
                    vlan_name=vlan_id_out_of_range['name'],
                    ip_addr=vlan_id_out_of_range['ip_addr'],
                    comment=vlan_id_out_of_range['comment']
                )
                assert vlan_page.get_required_field_message('整数范围 1~4090，以"-"连接id段，前值小于后值'), "未检测到VLAN ID范围提示"
                self._log_step('断言页面出现"整数范围 1~4090，以"-"连接id段，前值小于后值"提示', "success")
                # 校验名称不规范
                vlan_name_invalid = next((v for v in invalid_vlans if v['name'] == '56565'), None)
                self._log_step("【异常场景】名称不规范，尝试保存")
                vlan_page.add_vlan_with_partial_fields(
                    vlan_id=vlan_name_invalid['id'],
                    vlan_name=vlan_name_invalid['name'],
                    ip_addr=vlan_name_invalid['ip_addr'],
                    comment=vlan_name_invalid['comment']
                )
                assert vlan_page.get_required_field_message('名称必须以vlan开头，只支持数字、字母和_'), "未检测到VLAN名称规范提示"
                self._log_step('断言页面出现"名称必须以vlan开头，只支持数字、字母和_"提示', "success")
                # 校验IP不规范
                vlan_ip_invalid = next((v for v in invalid_vlans if v['ip_addr'] == '192.168.88.134343'), None)
                self._log_step("【异常场景】IP不规范，尝试保存")
                vlan_page.add_vlan_with_partial_fields(
                    vlan_id=vlan_ip_invalid['id'],
                    vlan_name=vlan_ip_invalid['name'],
                    ip_addr=vlan_ip_invalid['ip_addr'],
                    comment=vlan_ip_invalid['comment']
                )
                assert vlan_page.get_required_field_message('IP 必须是一个有效的地址'), "未检测到IP地址格式提示"
                self._log_step('断言页面出现"IP 必须是一个有效的地址"提示', "success")
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                print("[测试结束] test_add_vlan_invalid_fields", flush=True)
            except Exception as e:
                self._log_step(f"字段格式校验测试异常: {str(e)}", "error")
                print(f"[测试异常] test_add_vlan_invalid_fields: {str(e)}", flush=True)
                raise
    
    def test_enable_disable_vlan(self, logged_in_page, caplog):
        """VLAN启用/停用功能测试 - 单个和批量"""
        self.test_start_time = time.time()
        print("[测试开始] test_enable_disable_vlan", flush=True)
        if logged_in_page is None:
            pytest.skip("Playwright 不可用")
        with caplog.at_level(logging.INFO):
            try:
                test_case_config = self.vlan_data.get('test_cases', {}).get('test_enable_disable_vlan', {})
                basic_vlans = self.vlan_data.get('basic_vlans', [])
                vlan_page = VlanPage(logged_in_page)
                # 单独停用VLAN36
                vlan_id = basic_vlans[0]['id']
                self._log_step(f"单独停用VLAN{vlan_id}")
                assert vlan_page.disable_vlan(vlan_id), f"停用VLAN{vlan_id}失败"
                status = vlan_page.get_vlan_status(vlan_id)
                assert status == "已停用", f"VLAN{vlan_id}状态应为已停用，实际为{status}"
                self._log_step(f"VLAN{vlan_id}状态为{status}", "success")
                # 单独启用VLAN36
                self._log_step(f"单独启用VLAN{vlan_id}")
                assert vlan_page.enable_vlan(vlan_id), f"启用VLAN{vlan_id}失败"
                status = vlan_page.get_vlan_status(vlan_id)
                assert status == "已启用", f"VLAN{vlan_id}状态应为已启用，实际为{status}"
                self._log_step(f"VLAN{vlan_id}状态为{status}", "success")
                # 批量全选停用
                self._log_step("批量全选所有VLAN，点击停用")
                assert vlan_page.batch_disable_vlans(select_all=True), "批量停用失败"
                all_status = vlan_page.get_all_vlan_status()
                assert all(v == "已停用" for v in all_status.values()), f"存在未停用的VLAN: {all_status}"
                self._log_step("所有VLAN状态为已停用", "success")
                # 批量全选启用
                self._log_step("批量全选所有VLAN，点击启用")
                assert vlan_page.batch_enable_vlans(select_all=True), "批量启用失败"
                all_status = vlan_page.get_all_vlan_status()
                assert all(v == "已启用" for v in all_status.values()), f"存在未启用的VLAN: {all_status}"
                self._log_step("所有VLAN状态为已启用", "success")
                execution_time = time.time() - self.test_start_time
                self._log_step(f"执行耗时: {execution_time:.2f}秒")
                print("[测试结束] test_enable_disable_vlan", flush=True)
            except Exception as e:
                self._log_step(f"启用/停用测试异常: {str(e)}", "error")
                print(f"[测试异常] test_enable_disable_vlan: {str(e)}", flush=True)
                raise
    
    def test_export_import_vlan(self, logged_in_page, caplog):
        """VLAN导出导入功能测试（CSV + TXT）"""
        self.test_start_time = time.time()
        print("[测试开始] test_export_import_vlan", flush=True)

        if logged_in_page is None:
            pytest.skip("Playwright 不可用")

        with caplog.at_level(logging.INFO):
            vlan_page = VlanPage(logged_in_page)

            # 步骤 1: 导出 CSV 和 TXT
            self._log_step("步骤1: 导出CSV/TXT")
            csv_path = vlan_page.export_vlan("csv")
            txt_path = vlan_page.export_vlan("txt")
            assert csv_path and txt_path, "导出文件失败"

            # 步骤 2: 清空现有配置
            self._log_step("步骤2: 批量删除所有VLAN配置")
            assert vlan_page.delete_all_vlans(), "批量删除失败"

            # 步骤 3: 导入 CSV（不合并）
            self._log_step("步骤3: 导入CSV（覆盖模式）")
            assert vlan_page.import_vlan(csv_path, "csv", merge=False), "CSV 导入失败"

            # 步骤 4: 再次清空
            self._log_step("步骤4: 再次批量删除")
            assert vlan_page.delete_all_vlans(), "再次批量删除失败"

            # 步骤 5: 导入 TXT（合并）
            self._log_step("步骤5: 导入TXT（合并模式）")
            assert vlan_page.import_vlan(txt_path, "txt", merge=True), "TXT 导入失败"

            self._log_step("导出/导入流程完成", "success")

            # 清理下载文件
            try:
                for p in [csv_path, txt_path]:
                    if p and p.exists():
                        p.unlink()
            except Exception:
                pass

        print("[测试结束] test_export_import_vlan - 成功", flush=True)
    
    def get_execution_details(self):
        """获取执行详情（供报告生成器使用）"""
        return self.execution_details