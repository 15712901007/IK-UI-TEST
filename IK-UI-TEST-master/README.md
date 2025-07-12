# 路由器自动化测试项目

## 项目简介
基于Playwright + pytest + PySide6的路由器WEB界面自动化测试工具

## 技术栈
- 自动化框架: Playwright
- 测试框架: pytest  
- 数据驱动: YAML
- GUI界面: PySide6
- 日志系统: logging

## 安装步骤
1. pip install -r requirements.txt
2. playwright install chromium
3. 修改config/test_config.yaml配置
4. python main.py

## 项目结构
- config/: 配置文件
- data/: 测试数据
- pages/: 页面对象
- tests/: 测试用例
- utils/: 工具类
- gui/: GUI界面
- reports/: 测试报告
- logs/: 日志文件
- screenshots/: 测试截图

## 功能特性
1. 多功能测试支持
2. YAML数据驱动
3. GUI操作界面
4. 自定义测试报告
5. 实时日志监控
6. 失败自动截图
7. 循环批量执行
