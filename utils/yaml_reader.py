# YAML文件读取工具
import yaml
from pathlib import Path

class YamlReader:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
    
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
    
    def read_yaml(self, file_path: str):
        try:
            full_path = self.project_root / file_path
            
            if not full_path.exists():
                print(f"YAML文件不存在: {full_path}")
                return {}
            
            # 使用兼容的文件读取方法
            content = self._read_file_with_fallback(full_path)
            data = yaml.safe_load(content)
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
