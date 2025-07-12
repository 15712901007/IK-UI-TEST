# VLAN搜索功能测试说明

## 功能概述

根据您提供的界面截图，我已经为您的自动化测试项目添加了完整的VLAN搜索功能测试。该功能可以验证VLAN列表页面的搜索过滤功能。

## 新增文件和功能

### 1. 测试数据配置 (`data/vlan_data.yaml`)

在原有的VLAN测试数据基础上，新增了以下内容：

#### 搜索功能测试用例定义
```yaml
test_search_vlan:
  name: "VLAN搜索功能测试"
  business_scenario: "验证VLAN列表的搜索过滤功能，确保管理员能够快速定位特定的VLAN配置"
  test_steps:
    - "1. 导航到VLAN设置页面，确保有多个VLAN配置"
    - "2. 在搜索框中输入VLAN ID进行搜索"
    - "3. 验证搜索结果只显示匹配的VLAN记录"
    - "4. 清空搜索框，验证显示所有VLAN记录"
    - "5. 搜索VLAN名称，验证名称匹配功能"
    - "6. 搜索IP地址，验证IP地址匹配功能"
    - "7. 搜索不存在的内容，验证空结果显示"
    - "8. 测试搜索的实时过滤效果"
```

#### 搜索测试场景数据
```yaml
search_test_data:
  search_scenarios:
    - search_type: "vlan_id"
      search_term: "36"
      expected_count: 1
      expected_vlans: ["36"]
      description: "按VLAN ID搜索"
    
    - search_type: "vlan_name"
      search_term: "vlan201"
      expected_count: 1
      expected_vlans: ["201"]
      description: "按VLAN名称搜索"
    
    - search_type: "ip_address"
      search_term: "192.168.36"
      expected_count: 1
      expected_vlans: ["36"]
      description: "按IP地址搜索"
    
    - search_type: "partial_match"
      search_term: "20"
      expected_count: 3
      expected_vlans: ["201", "202", "203"]
      description: "部分匹配搜索"
    
    - search_type: "no_match"
      search_term: "999"
      expected_count: 0
      expected_vlans: []
      description: "无匹配结果搜索"
    
    - search_type: "empty_search"
      search_term: ""
      expected_count: "all"
      expected_vlans: []
      description: "空搜索显示所有结果"
```

### 2. 页面对象方法 (`pages/vlan_page.py`)

#### 新增搜索相关元素选择器
```python
# 搜索功能相关元素
self.search_input = "input[placeholder*='VlanID/Vlan名称/IP/备注']"
self.search_input_alt = "input[type='text']"  # 备用选择器
self.search_clear_btn = "button[aria-label='Clear']"
```

#### 新增搜索功能方法

1. **`search_vlan(search_term: str)`** - 执行搜索操作
2. **`get_filtered_vlan_list()`** - 获取过滤后的VLAN列表
3. **`clear_search()`** - 清空搜索框
4. **`verify_search_results(search_term: str, expected_vlans: list)`** - 验证搜索结果

### 3. 测试用例 (`tests/test_vlan.py`)

新增了 `test_search_vlan` 测试方法，该方法会：

1. 确保有足够的测试数据
2. 执行多种搜索场景测试
3. 验证搜索结果的准确性
4. 测试实时过滤效果
5. 生成详细的测试报告

### 4. 独立测试脚本 (`test_vlan_search.py`)

创建了一个独立的搜索功能测试脚本，可以单独运行搜索功能测试。

## 使用方法

### 1. 运行完整的VLAN测试（包含搜索功能）

```bash
# 运行所有VLAN测试
python -m pytest tests/test_vlan.py -v

# 只运行搜索功能测试
python -m pytest tests/test_vlan.py::TestVlan::test_search_vlan -v
```

### 2. 使用GUI工具运行

在您的GUI工具中，选择"VLAN设置"功能，新的搜索功能测试会自动包含在测试流程中。

### 3. 查看测试数据

```bash
# 查看搜索测试场景
python test_vlan_search.py
```

## 测试场景说明

### 按VLAN ID搜索
- 搜索内容：`36`
- 期望结果：只显示VLAN ID为36的记录

### 按VLAN名称搜索
- 搜索内容：`vlan201`
- 期望结果：只显示名称为vlan201的记录

### 按IP地址搜索
- 搜索内容：`192.168.36`
- 期望结果：只显示IP地址包含192.168.36的记录

### 部分匹配搜索
- 搜索内容：`20`
- 期望结果：显示所有包含"20"的VLAN记录（201、202、203）

### 无匹配结果搜索
- 搜索内容：`999`
- 期望结果：不显示任何记录

### 空搜索测试
- 搜索内容：（空）
- 期望结果：显示所有VLAN记录

## 搜索功能特点

1. **实时过滤** - 输入搜索内容时立即过滤结果
2. **多字段匹配** - 支持按VLAN ID、名称、IP地址、备注搜索
3. **部分匹配** - 支持模糊搜索
4. **清空功能** - 可以清空搜索框恢复所有结果
5. **结果验证** - 自动验证搜索结果的准确性

## 测试报告

测试完成后会生成详细的中文测试报告，包含：

- 搜索功能测试结果
- 各个搜索场景的执行情况
- 搜索性能和准确性分析
- 失败场景的详细信息

## 注意事项

1. **搜索框定位** - 脚本会尝试多种选择器来定位搜索框，以适应不同的UI变化
2. **结果验证** - 搜索结果验证基于可见的表格行，确保过滤效果正确
3. **测试数据** - 如果系统中VLAN数量不足，测试会自动添加必要的测试数据
4. **等待时间** - 搜索操作后会等待适当时间确保结果更新

## 扩展说明

如果您需要添加更多的搜索场景，可以在 `data/vlan_data.yaml` 的 `search_scenarios` 部分添加新的测试场景。每个场景包含：

- `search_type`: 搜索类型标识
- `search_term`: 搜索内容
- `expected_count`: 期望结果数量
- `expected_vlans`: 期望的VLAN ID列表
- `description`: 场景描述

这样您就可以根据实际需求灵活配置搜索测试场景了。 