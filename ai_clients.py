"""AI 渠道客户端：OpenAI 兼容 HTTP API 与本机 Codex CLI app-server。"""
from collections import deque
import glob
import json
import os
import queue
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.request


PROVIDER_OPENAI = "openai_compatible"
PROVIDER_CODEX = "codex_cli"


class AIClientError(RuntimeError):
    """面向设置窗口和作者提取流程的可读错误。"""


def _api_url(api_base, endpoint):
    base = (api_base or "").strip().rstrip("/")
    if not base:
        raise AIClientError("未配置 API Base")
    return base + "/" + endpoint.lstrip("/")


def _auth_headers(api_key, *, json_body=False):
    headers = {}
    key = (api_key or "").strip()
    if key:
        headers["Authorization"] = "Bearer " + key
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _http_error_message(exc):
    detail = ""
    try:
        raw = exc.read().decode("utf-8", errors="replace")
        body = json.loads(raw)
        detail = body.get("error", {}).get("message", "")
        if not detail:
            detail = raw[:300]
    except Exception:
        pass
    suffix = f": {detail}" if detail else ""
    return f"HTTP {getattr(exc, 'code', '?')}{suffix}"


def _read_json_response(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise AIClientError(_http_error_message(exc)) from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise AIClientError(f"无法连接接口: {reason}") from exc
    except json.JSONDecodeError as exc:
        raise AIClientError("接口返回的不是有效 JSON") from exc


def fetch_openai_models(api_base, api_key, timeout=30):
    """从 OpenAI 兼容渠道的 GET /models 获取可用模型 ID。"""
    req = urllib.request.Request(
        _api_url(api_base, "models"),
        headers=_auth_headers(api_key),
        method="GET",
    )
    body = _read_json_response(req, timeout)
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, list):
        raise AIClientError("模型接口缺少 data 数组")
    models = []
    seen = set()
    for item in data:
        model_id = item.get("id") if isinstance(item, dict) else None
        if isinstance(model_id, str) and model_id.strip() and model_id not in seen:
            seen.add(model_id)
            models.append(model_id)
    if not models:
        raise AIClientError("渠道未返回任何模型")
    return sorted(models, key=str.lower)


def call_openai_chat(cfg, user_content, *, max_tokens=1000):
    """调用 OpenAI 兼容的 chat/completions。"""
    model = (cfg.get("model") or "").strip()
    if not model:
        raise AIClientError("未填写模型名")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": cfg.get("prompt", "")},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        _api_url(cfg.get("api_base"), "chat/completions"),
        data=json.dumps(payload).encode("utf-8"),
        headers=_auth_headers(cfg.get("api_key"), json_body=True),
        method="POST",
    )
    body = _read_json_response(req, 120)
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIClientError("接口响应缺少 choices[0].message.content") from exc
    if not isinstance(content, str) or not content.strip():
        raise AIClientError("模型返回内容为空")
    return content


def test_openai_connection(cfg):
    test_cfg = dict(cfg)
    test_cfg["prompt"] = "这是连接测试。不要调用工具，只回复 OK。"
    reply = call_openai_chat(test_cfg, "只回复 OK", max_tokens=8)
    return f"连接成功，模型返回：{reply.strip()[:80]}"


def find_codex_cli(configured_path=""):
    """优先找用户可执行的 Codex CLI，避开可能受限的 WindowsApps 内部路径。"""
    configured = os.path.expandvars(os.path.expanduser((configured_path or "").strip()))
    if configured:
        if os.path.isfile(configured):
            return os.path.abspath(configured)
        resolved = shutil.which(configured)
        if resolved:
            return resolved

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        pattern = os.path.join(local_app_data, "OpenAI", "Codex", "bin", "*", "codex.exe")
        candidates = [p for p in glob.glob(pattern) if os.path.isfile(p)]
        if candidates:
            return max(candidates, key=os.path.getmtime)

    return shutil.which("codex.exe") or shutil.which("codex")


class CodexAppServer:
    """Codex app-server 的最小 JSON-RPC stdio 客户端。"""

    def __init__(self, cli_path="", cwd=None, timeout=30):
        self.cli_path = find_codex_cli(cli_path)
        self.cwd = cwd or os.getcwd()
        self.timeout = timeout
        self.process = None
        self._next_id = 1
        self._response_queues = {}
        self._response_lock = threading.Lock()
        self.events = queue.Queue()
        self.stderr_tail = deque(maxlen=40)

    def __enter__(self):
        if not self.cli_path:
            raise AIClientError("未找到 Codex CLI，请在设置中指定 codex.exe")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            self.process = subprocess.Popen(
                [self.cli_path, "app-server", "--listen", "stdio://"],
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise AIClientError(f"无法启动 Codex CLI: {exc}") from exc
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "karihelper",
                    "title": "KariHelper",
                    "version": "1.0.0",
                }
            },
        )
        self.notify("initialized")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def _read_stdout(self):
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            request_id = message.get("id")
            if request_id is not None and ("result" in message or "error" in message):
                with self._response_lock:
                    target = self._response_queues.get(request_id)
                if target:
                    target.put(message)
            else:
                self.events.put(message)

    def _read_stderr(self):
        assert self.process and self.process.stderr
        for line in self.process.stderr:
            text = line.strip()
            if text:
                self.stderr_tail.append(text)

    def _send(self, message):
        if not self.process or not self.process.stdin:
            raise AIClientError("Codex app-server 未启动")
        try:
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise AIClientError(self._exit_message()) from exc

    def request(self, method, params=None, timeout=None):
        request_id = self._next_id
        self._next_id += 1
        target = queue.Queue(maxsize=1)
        with self._response_lock:
            self._response_queues[request_id] = target
        self._send({"method": method, "id": request_id, "params": params or {}})
        deadline = time.monotonic() + (timeout or self.timeout)
        try:
            while True:
                if self.process and self.process.poll() is not None:
                    raise AIClientError(self._exit_message())
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AIClientError(f"Codex 请求超时: {method}")
                try:
                    response = target.get(timeout=min(0.2, remaining))
                    break
                except queue.Empty:
                    continue
        finally:
            with self._response_lock:
                self._response_queues.pop(request_id, None)
        if response.get("error"):
            error = response["error"]
            detail = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            raise AIClientError(f"Codex {method} 失败: {detail}")
        return response.get("result", {})

    def notify(self, method, params=None):
        self._send({"method": method, "params": params or {}})

    def respond(self, request_id, result):
        self._send({"id": request_id, "result": result})

    def next_event(self, timeout=0.2):
        try:
            return self.events.get(timeout=timeout)
        except queue.Empty:
            if self.process and self.process.poll() is not None:
                raise AIClientError(self._exit_message())
            return None

    def _exit_message(self):
        details = " | ".join(self.stderr_tail)
        return "Codex app-server 已退出" + (f": {details[-600:]}" if details else "")

    def close(self):
        process = self.process
        self.process = None
        if not process or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def fetch_codex_models(cli_path="", cwd=None, timeout=30):
    """通过 Codex app-server model/list 获取 ChatGPT/Codex 可用模型。"""
    models = []
    seen = set()
    cursor = None
    with CodexAppServer(cli_path, cwd=cwd, timeout=timeout) as server:
        while True:
            params = {"limit": 200, "includeHidden": False}
            if cursor:
                params["cursor"] = cursor
            result = server.request("model/list", params, timeout=timeout)
            for item in result.get("data", []):
                model_id = item.get("model") or item.get("id")
                if isinstance(model_id, str) and model_id and model_id not in seen:
                    seen.add(model_id)
                    models.append(model_id)
            cursor = result.get("nextCursor")
            if not cursor:
                break
    if not models:
        raise AIClientError("Codex 未返回任何可用模型，请检查登录状态")
    return models


def run_codex_prompt(cli_path, model, prompt, *, output_schema=None, cwd=None, timeout=180):
    """通过 Codex app-server 运行一次只读模型请求并返回最终文本。"""
    model = (model or "").strip()
    if not model:
        raise AIClientError("未填写模型名")
    cwd = cwd or os.getcwd()
    with CodexAppServer(cli_path, cwd=cwd, timeout=min(timeout, 45)) as server:
        thread_result = server.request(
            "thread/start",
            {
                "model": model,
                "cwd": cwd,
                "approvalPolicy": "never",
                "sandbox": "readOnly",
                "serviceName": "karihelper",
            },
            timeout=45,
        )
        thread_id = thread_result.get("thread", {}).get("id")
        if not thread_id:
            raise AIClientError("Codex 未返回 thread id")
        turn_params = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": prompt}],
            "model": model,
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "readOnly", "access": {"type": "fullAccess"}},
        }
        if output_schema:
            turn_params["outputSchema"] = output_schema
        server.request("turn/start", turn_params, timeout=45)

        final_text = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            event = server.next_event(timeout=min(0.25, max(0.01, deadline - time.monotonic())))
            if not event:
                continue
            method = event.get("method")
            params = event.get("params") or {}
            if event.get("id") is not None and method:
                if method.endswith("requestApproval"):
                    server.respond(event["id"], {"decision": "decline"})
                else:
                    server.respond(event["id"], {})
                continue
            if method == "item/completed":
                item = params.get("item") or {}
                if item.get("type") == "agentMessage" and item.get("text"):
                    final_text = item["text"]
            elif method == "turn/completed":
                turn = params.get("turn") or {}
                if turn.get("status") == "failed":
                    error = turn.get("error") or {}
                    raise AIClientError(error.get("message", "Codex 模型请求失败"))
                if not final_text.strip():
                    raise AIClientError("Codex 模型返回内容为空")
                return final_text
        raise AIClientError("Codex 模型响应超时")


def test_codex_connection(cfg, cwd=None):
    reply = run_codex_prompt(
        cfg.get("codex_cli_path", ""),
        cfg.get("model", ""),
        "这是连接测试。不要使用任何工具，只回复 OK。",
        cwd=cwd,
        timeout=120,
    )
    return f"连接成功，模型返回：{reply.strip()[:80]}"
