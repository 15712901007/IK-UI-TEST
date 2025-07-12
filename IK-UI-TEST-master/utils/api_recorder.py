import json
import time
from pathlib import Path
from typing import Dict, Any


def _format_curl(request_url: str, method: str, headers: Dict[str, str], body: str | None = None) -> str:
    """根据请求信息构造 curl bash 命令字符串"""
    parts: list[str] = [f"curl -X {method.upper()} '{request_url}' \\"]
    for k, v in headers.items():
        parts.append(f"  -H '{k}: {v}' \\")
    if body:
        # 将换行及单引号简单转义
        safe_body = body.replace("'", "'\\''")
        parts.append(f"  -d '{safe_body}' ")
    # 移除最后行可能的反斜杠空格
    if parts[-1].endswith(" "):
        parts[-1] = parts[-1].rstrip()
    return "\n".join(parts)


def save_api_call(name: str, request, response, base_dir: str = "api_logs/vlan", use_timestamp: bool = True) -> tuple[Path, Path]:
    """保存接口请求/响应详情到文件，并生成 curl 命令

    参数:
        name: 逻辑名称，如 add_vlan36
        request: Playwright.Request 对象
        response: Playwright.Response 对象
        base_dir: 保存目录
        use_timestamp: 是否在文件名中包含时间戳
    返回: (json文件路径, curl文件路径)
    """
    ts = int(time.time())
    dir_path = Path(base_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    if use_timestamp:
        file_path = dir_path / f"{name}_{ts}.json"
    else:
        file_path = dir_path / f"{name}.json"

    # headers
    # Playwright 的 headers() 可能省略 Cookie，用 all_headers() 可拿到完整数据
    try:
        req_headers = dict(request.all_headers())  # type: ignore
    except Exception:
        req_headers = dict(request.headers)
    resp_headers = dict(response.headers)

    # body
    try:
        body = request.post_data or ""
    except Exception:
        body = ""

    # 生成 python requests 片段
    def _format_python(url: str, hdrs: Dict[str, str], body: str | None):
        py = ["import requests, json", f"url = '{url}'", f"headers = {json.dumps(hdrs, ensure_ascii=False, indent=2)}"]
        if body:
            py.append(f"data = {json.dumps(body, ensure_ascii=False)}")
            py.append("resp = requests.post(url, headers=headers, data=data, verify=False)")
        else:
            py.append("resp = requests.get(url, headers=headers, verify=False)")
        py.append("print(resp.text)")
        return "\n".join(py)

    curl_cmd = _format_curl(request.url, request.method, req_headers, body)

    data: Dict[str, Any] = {
        "timestamp": ts,
        "url": request.url,
        "method": request.method,
        "request_headers": req_headers,
        "request_body": body,
        "response_status": response.status,
        "response_headers": resp_headers,
        "response_body": None,
        "curl": curl_cmd,
        "python": _format_python(request.url, req_headers, body),
    }

    # 尝试解析响应 json
    try:
        data["response_body"] = response.json()
    except Exception:
        try:
            data["response_body"] = response.text()[:2000]
        except Exception:
            data["response_body"] = "<binary>"

    # 生成文件名
    if use_timestamp:
        json_filename = f"{name}_{ts}.json"
        curl_filename = f"{name}_{ts}.curl"
    else:
        json_filename = f"{name}.json"
        curl_filename = f"{name}.curl"
    
    json_file_path = dir_path / json_filename
    curl_file_path = dir_path / curl_filename
    
    # 保存curl命令到单独的文件（纯文本，无引号）
    with open(curl_file_path, "w", encoding="utf-8") as f:
        f.write(curl_cmd)
    
    # 从data中移除curl字段，保存到JSON文件
    data_without_curl = data.copy()
    del data_without_curl["curl"]
    
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(data_without_curl, f, ensure_ascii=False, indent=2)

    return json_file_path, curl_file_path 