# YAML文件读取工具
import yaml
from pathlib import Path

class YamlReader:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
    
    def read_yaml(self, file_path: str):
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                print(f"YAML文件不存在: {full_path}")
                return {}
            
            with open(full_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                return data or {}
                
        except yaml.YAMLError as e:
            print(f"YAML文件格式错误 {file_path}: {e}")
            return {}
        except Exception as e:
            print(f"读取YAML文件失败 {file_path}: {e}")
            return {}
    
    def write_yaml(self, file_path: str, data: dict):
        try:
            full_path = self.project_root / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
                return True
                
        except Exception as e:
            print(f"写入YAML文件失败 {file_path}: {e}")
            return False
