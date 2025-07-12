from pathlib import Path

# 专用的导出文件目录，所有测试产生的下载/导出文件统一存放于此
DOWNLOAD_DIR = Path(__file__).parent.parent / "exports"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True) 