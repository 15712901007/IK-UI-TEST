# 命令行测试执行入口
import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_tests(test_modules=None, cycles=1):
    print(f"开始执行测试...")
    print(f"测试模块: {test_modules}")
    print(f"循环次数: {cycles}")
    
    # 这里需要集成pytest执行
    try:
        import pytest
        pytest_args = ["-v"]
        
        if test_modules:
            for module in test_modules:
                pytest_args.append(f"tests/test_{module}.py")
        else:
            pytest_args.append("tests/")
        
        for cycle in range(cycles):
            print(f"第 {cycle + 1} 轮测试")
            result = pytest.main(pytest_args)
            
    except ImportError:
        print("pytest 未安装，请先安装：pip install pytest")

def main():
    parser = argparse.ArgumentParser(description="路由器自动化测试")
    parser.add_argument("--modules", nargs="+", help="指定测试模块")
    parser.add_argument("--cycles", type=int, default=1, help="测试循环次数")
    
    args = parser.parse_args()
    run_tests(test_modules=args.modules, cycles=args.cycles)

if __name__ == "__main__":
    main()
