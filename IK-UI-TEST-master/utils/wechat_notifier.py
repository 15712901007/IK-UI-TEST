# 企业微信通知工具
import requests
import json
from utils.logger import Logger

class WechatNotifier:
    """企业微信通知器"""
    
    def __init__(self, webhook_url=""):
        self.webhook_url = webhook_url
        self.logger = Logger().get_logger()
    
    def send_message(self, content, msg_type="text"):
        """发送消息"""
        if not self.webhook_url:
            self.logger.warning("企业微信webhook未配置")
            return False
            
        try:
            data = {
                "msgtype": msg_type,
                msg_type: {
                    "content": content
                }
            }
            
            response = requests.post(
                self.webhook_url,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('errcode') == 0:
                    self.logger.info("企业微信消息发送成功")
                    return True
                else:
                    self.logger.error(f"企业微信消息发送失败: {result.get('errmsg', '未知错误')}")
                    return False
            else:
                self.logger.error(f"企业微信API请求失败: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error("企业微信消息发送超时")
            return False
        except Exception as e:
            self.logger.error(f"发送企业微信消息失败: {e}")
            return False
    
    def send_markdown(self, content):
        """发送Markdown格式消息"""
        return self.send_message(content, "markdown")
    
    def send_test_result(self, test_name, success, details="", test_stats=None):
        """发送测试结果通知"""
        status_emoji = "✅" if success else "❌"
        status_text = "成功" if success else "失败"
        
        content = f"""
🤖 **路由器自动化测试结果通知**

📋 **测试信息:**
- 测试名称: {test_name}
- 测试状态: {status_emoji} {status_text}
- 通知时间: {self._get_current_time()}

"""
        
        if test_stats:
            content += f"""📊 **统计信息:**
- 总用例数: {test_stats.get('total', 0)}
- 成功: {test_stats.get('passed', 0)}
- 失败: {test_stats.get('failed', 0)}
- 跳过: {test_stats.get('skipped', 0)}
- 成功率: {test_stats.get('success_rate', 0):.1f}%

"""
        
        if details:
            content += f"""💬 **详细信息:**
{details}
"""
        
        return self.send_markdown(content.strip())
    
    def send_test_start_notification(self, test_config):
        """发送测试开始通知"""
        content = f"""
🚀 **路由器自动化测试开始**

📋 **测试配置:**
- 路由器IP: {test_config.get('router', {}).get('ip', '未知')}
- 测试功能: {test_config.get('test_function', '全部功能')}
- 循环次数: {test_config.get('cycles', 1)}
- 测试人员: {test_config.get('test_info', {}).get('tester', '未知')}
- 开始时间: {self._get_current_time()}

⏳ 测试执行中，请稍候...
        """
        
        return self.send_markdown(content.strip())
    
    def _get_current_time(self):
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')