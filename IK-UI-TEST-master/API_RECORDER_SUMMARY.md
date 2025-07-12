# API记录功能实现总结

## 功能概述

已成功实现了UI自动化测试中的API接口记录功能，可以在执行VLAN操作时自动捕获并保存API调用信息。

## 主要改进

### 1. 双文件输出格式
- **JSON文件**: 包含完整的请求/响应信息（不含curl字段）
- **CURL文件**: 单独的curl命令文件，可直接复制执行

### 2. 文件命名规则
- JSON文件: `{operation_name}.json`
- CURL文件: `{operation_name}.curl`
- 支持时间戳命名（可选）

### 3. CURL格式优化
- 真正的多行格式，每行以 `\` 结尾
- 无引号包围，可直接复制到终端执行
- 包含完整的Cookie信息，支持会话复用

### 4. 支持的VLAN操作
- ✅ 添加VLAN (`add_vlan_36`)
- ✅ 启用VLAN (`enable_vlan_36`)
- ✅ 停用VLAN (`disable_vlan_36`)
- ✅ 批量启用 (`batch_enable_all`)
- ✅ 批量停用 (`batch_disable_all`)
- ✅ 查询VLAN (`show_vlan_*`)
- 🔄 导出VLAN (`export_vlan_*`)
- 🔄 导入VLAN (`import_vlan_*`)
- 🔄 删除VLAN (`delete_vlan_*`)

## 文件结构

```
api_logs/vlan/
├── add_vlan_36.json        # 完整API信息
├── add_vlan_36.curl        # 可执行的curl命令
├── enable_vlan_36.json
├── enable_vlan_36.curl
├── disable_vlan_36.json
├── disable_vlan_36.curl
└── ...
```

## 使用示例

### JSON文件内容
```json
{
  "timestamp": 1752214788,
  "url": "http://10.66.0.40/Action/call",
  "method": "POST",
  "request_headers": {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "cookie": "sess_key=xxx; username=admin; login=1"
  },
  "request_body": "{\"func_name\":\"vlan\",\"action\":\"add\",\"param\":{...}}",
  "response_status": 200,
  "response_headers": {...},
  "response_body": {"Result": 30000, "ErrMsg": "Success"},
  "python": "import requests, json\n..."
}
```

### CURL文件内容
```bash
curl -X POST 'http://10.66.0.40/Action/call' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'content-type: application/json;charset=UTF-8' \
  -H 'cookie: sess_key=xxx; username=admin; login=1' \
  -d '{"func_name":"vlan","action":"add","param":{"vlan_id":"36","vlan_name":"vlan36"}}'
```

## 技术实现

### 1. API监听机制
- 使用 `page.on("requestfinished")` 全局监听
- 过滤 `POST /Action/call` 请求
- 匹配 `"func_name":"vlan"` 请求体
- 解析 `action` 字段确定操作类型

### 2. 自动保存逻辑
- 在每个VLAN操作方法中设置监听器
- 操作完成后自动保存API记录
- 支持多种操作类型的文件命名

### 3. 兼容性处理
- 支持不同版本的Playwright API
- 处理 `page.off()` 和 `page.remove_listener()` 兼容性
- 错误处理和日志记录

## 日志输出示例

```
[API-ADD] JSON: api_logs\vlan\add_vlan_36.json
[API-ADD] CURL: api_logs\vlan\add_vlan_36.curl
[API-ENABLE] JSON: api_logs\vlan\enable_vlan_36.json
[API-ENABLE] CURL: api_logs\vlan\enable_vlan_36.curl
```

## 复用方式

### 1. 直接复制CURL命令
```bash
# 从 .curl 文件直接复制到终端执行
curl -X POST 'http://10.66.0.40/Action/call' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'cookie: sess_key=xxx; username=admin; login=1' \
  -d '{"func_name":"vlan","action":"add","param":{...}}'
```

### 2. 使用Python代码
```python
# 从JSON文件中的python字段复制
import requests, json
url = 'http://10.66.0.40/Action/call'
headers = {...}
data = "{...}"
resp = requests.post(url, headers=headers, data=data, verify=False)
print(resp.text)
```

## 优势

1. **便于调试**: 可以快速复现UI操作对应的API调用
2. **接口复用**: 提供curl和Python两种复用方式
3. **会话保持**: 包含完整Cookie信息，支持会话复用
4. **格式友好**: curl命令格式化，易于阅读和执行
5. **自动化**: 无需手动抓包，自动记录所有VLAN操作

## 后续扩展

- [ ] 支持更多路由器功能模块（端口映射、ACL等）
- [ ] 添加API调用时间统计
- [ ] 支持API调用链分析
- [ ] 集成到测试报告中 