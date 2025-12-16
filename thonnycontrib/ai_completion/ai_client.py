"""
AI 客户端模块
负责与 AI 服务进行交互，发送代码分析请求并处理响应
"""
import json
import time
from datetime import datetime
from logging import getLogger
from typing import Dict, Any, Optional

logger = getLogger(__name__)


class AIClient:
    """AI 代码分析客户端"""

    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None, model: Optional[str] = None):
        """
        初始化 AI 客户端
        
        Args:
            api_key: API 密钥（如果为 None，将尝试从配置加载）
            endpoint: API 端点 URL（如果为 None，将使用默认值或从配置加载）
            model: AI 模型名称（如果为 None，将使用默认值或从配置加载）
        """
        self.api_key = api_key
        self.endpoint = endpoint or "https://api.example.com/v1/chat/completions"
        self.model = model or "gpt-3.5-turbo"
        
        # 尝试从配置加载（如果未提供
        if not self.api_key:
            self._load_config()
        
        logger.info(f"AIClient initialized with endpoint: {self.endpoint}, model: {self.model}")

    def _load_config(self):
        """从配置文件加载 API 配置"""
        try:
            # 从 ai_config 模块加载配置（修复导入路径）
            from .ai_config import get_ai_config
            config = get_ai_config()
            
            if not self.api_key:
                self.api_key = config.get("api_key")
            if not self.endpoint or self.endpoint == "https://api.example.com/v1/chat/completions":
                self.endpoint = config.get("endpoint", self.endpoint)
            if not self.model or self.model == "gpt-3.5-turbo":
                self.model = config.get("model", self.model)
            
            logger.debug(f"Loaded config: endpoint={self.endpoint}, model={self.model}, api_key={'*' * 6 if self.api_key else 'None'}")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            # 配置加载失败时，API 将无法使用
            # 用户需要在设置中配置 API
            logger.warning("No API configuration available. Please configure in Settings.")

    def request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送代码分析/补全请求到 AI 服务
        
        Args:
            context: 包含以下键的字典：
                - text: 完整代码文本（或上下文窗口内的代码）
                - prefix: 光标前的代码（用于补全模式）
                - suffix: 光标后的代码（用于补全模式）
                - selection: 选中的代码（如果有）
                - language: 编程语言
                - filename: 文件名
                - mode: "completion" 或 "analysis"（默认）
        
        Returns:
            包含以下键的字典：
                - success: 是否成功
                - data: 结果数据（如果成功）
                    - raw_analysis: AI 分析/补全结果文本
                    - metadata: 元数据
                - timestamp: 时间戳
                - message: 错误消息（如果失败）
        """
        try:
            # 提取上下文信息
            code_text = context.get("text", "")
            selected_code = context.get("selection", "")
            language = context.get("language", "python")
            filename = context.get("filename", "Untitled.py")
            mode = context.get("mode", "analysis")
            
            logger.info(f"Requesting AI {mode} for {filename} ({language})")
            
            # 始终使用真实 API 调用（不使用模拟模式）
            return self._make_api_request(context)
            
        except Exception as e:
            logger.error(f"Error in AI request: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Request failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def _simulate_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟 AI 请求（用于测试或当 API 未配置时）
        
        Args:
            context: 请求上下文
        
        Returns:
            模拟的响应结果
        """
        code_text = context.get("text", "")
        selected_code = context.get("selection", "")
        language = context.get("language", "python")
        filename = context.get("filename", "Untitled.py")
        mode = context.get("mode", "analysis")
        prefix = context.get("prefix", "")
        
        # Sprint 3: 根据模式生成不同的结果
        if mode == "completion":
            # 补全模式：生成代码片段
            analysis_text = self._generate_mock_completion(prefix, language)
        else:
            # 分析模式：生成分析报告
            analysis_text = f"""代码分析报告（模拟模式）

文件: {filename}
语言: {language}
代码长度: {len(code_text)} 字符
选中代码长度: {len(selected_code)} 字符

分析结果:
----------
这是一个模拟的 AI 代码分析结果。

当前代码包含 {len(code_text.splitlines())} 行代码。

建议(test):
1. 这是一个占位符分析结果
2. 请配置真实的 API 密钥以获取实际分析
3. 在设置中配置 API Key、Endpoint 和 Model

注意: 当前使用的是模拟模式，不会调用真实的 AI 服务。
"""
        
        metadata = {
            "filename": filename,
            "language": language,
            "code_length": len(code_text),
            "selection_length": len(selected_code),
            "line_count": len(code_text.splitlines()),
            "mode": mode
        }
        
        return {
            "success": True,
            "data": {
                "raw_analysis": analysis_text,
                "metadata": metadata
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_mock_completion(self, prefix: str, language: str) -> str:
        """
        生成智能代码补全（本地模式）
        根据上下文生成实际有用的代码建议
        """
        prefix_lines = prefix.strip().splitlines() if prefix else []
        last_line = prefix_lines[-1] if prefix_lines else ""
        last_line_stripped = last_line.strip()
        
        # 获取当前缩进
        indent = ""
        for char in last_line:
            if char in (' ', '\t'):
                indent += char
            else:
                break
        next_indent = indent + "    "
        
        if language == "python":
            # ===== 函数定义 =====
            # def hello → def hello(name):
            if last_line_stripped.startswith("def ") and "(" not in last_line_stripped:
                func_name = last_line_stripped[4:].strip()
                # 根据函数名猜测参数
                if "get" in func_name.lower():
                    return f"(key, default=None):\n{next_indent}\"\"\"Get value by key.\"\"\"\n{next_indent}return self.data.get(key, default)"
                elif "set" in func_name.lower():
                    return f"(key, value):\n{next_indent}\"\"\"Set value for key.\"\"\"\n{next_indent}self.data[key] = value"
                elif "is_" in func_name.lower() or "has_" in func_name.lower():
                    return f"(value):\n{next_indent}\"\"\"Check condition.\"\"\"\n{next_indent}return value is not None"
                elif "hello" in func_name.lower() or "greet" in func_name.lower():
                    return f"(name=\"World\"):\n{next_indent}\"\"\"Print a greeting message.\"\"\"\n{next_indent}print(f\"Hello, {{name}}!\")"
                elif "add" in func_name.lower():
                    return f"(a, b):\n{next_indent}\"\"\"Add two numbers.\"\"\"\n{next_indent}return a + b"
                elif "create" in func_name.lower() or "make" in func_name.lower():
                    return f"(data):\n{next_indent}\"\"\"Create a new instance.\"\"\"\n{next_indent}return cls(data)"
                elif "process" in func_name.lower():
                    return f"(data):\n{next_indent}\"\"\"Process the input data.\"\"\"\n{next_indent}result = []\n{next_indent}for item in data:\n{next_indent}    result.append(item)\n{next_indent}return result"
                elif "calculate" in func_name.lower() or "calc" in func_name.lower():
                    return f"(x, y):\n{next_indent}\"\"\"Calculate result.\"\"\"\n{next_indent}return x * y"
                elif "read" in func_name.lower():
                    return f"(filename):\n{next_indent}\"\"\"Read file contents.\"\"\"\n{next_indent}with open(filename, 'r') as f:\n{next_indent}    return f.read()"
                elif "write" in func_name.lower():
                    return f"(filename, content):\n{next_indent}\"\"\"Write content to file.\"\"\"\n{next_indent}with open(filename, 'w') as f:\n{next_indent}    f.write(content)"
                elif "main" in func_name.lower():
                    return f"():\n{next_indent}\"\"\"Main entry point.\"\"\"\n{next_indent}print(\"Hello, World!\")"
                else:
                    return f"():\n{next_indent}\"\"\"TODO: Add description.\"\"\"\n{next_indent}pass"
            
            # def hello(): 后补全函数体
            if last_line_stripped.startswith("def ") and last_line_stripped.endswith(":"):
                return f"\n{next_indent}pass"
            
            # ===== 类定义 =====
            if last_line_stripped.startswith("class ") and ":" not in last_line_stripped:
                class_name = last_line_stripped[6:].strip()
                return f":\n{next_indent}\"\"\"A {class_name} class.\"\"\"\n{next_indent}\n{next_indent}def __init__(self):\n{next_indent}    self.data = {{}}"
            
            # ===== 循环 =====
            if last_line_stripped.startswith("for ") and " in " not in last_line_stripped:
                var = last_line_stripped[4:].strip() or "i"
                return f" in range(10):\n{next_indent}print({var})"
            
            if last_line_stripped == "for":
                return " i in range(10):\n{next_indent}print(i)"
            
            # ===== 条件语句 =====
            if last_line_stripped == "if":
                return " condition:\n{next_indent}pass"
            
            if last_line_stripped.startswith("if ") and not last_line_stripped.endswith(":"):
                return ":\n{next_indent}pass"
            
            # ===== print =====
            if last_line_stripped == "print(" or last_line_stripped == "print":
                return '("Hello, World!")'
            
            # ===== import =====
            if last_line_stripped == "import":
                return " os"
            if last_line_stripped == "from":
                return " typing import List, Dict, Optional"
            
            # ===== 冒号后 =====
            if last_line_stripped.endswith(":"):
                return f"\n{next_indent}pass"
            
            # ===== while =====
            if last_line_stripped == "while":
                return " True:\n{next_indent}break"
            
            # ===== try =====
            if last_line_stripped == "try":
                return f":\n{next_indent}pass\n{indent}except Exception as e:\n{next_indent}print(f\"Error: {{e}}\")"
            
            # ===== with =====
            if last_line_stripped == "with":
                return f" open('file.txt', 'r') as f:\n{next_indent}content = f.read()"
            
            # ===== return =====
            if last_line_stripped == "return":
                return " None"
            
            # ===== 括号补全 =====
            if last_line_stripped.endswith("["):
                return "]"
            if last_line_stripped.endswith("{"):
                return "}"
            if last_line_stripped.endswith("("):
                return ")"
            
            # 默认：空建议（不打扰用户）
            return ""
        
        elif language in ("javascript", "typescript"):
            if last_line_stripped.startswith("function"):
                return "() {\n    // TODO\n}"
            if last_line_stripped.startswith("const ") and "=" not in last_line_stripped:
                return " = null;"
            return "// TODO"
        
        else:
            return "// AI suggestion placeholder"

    def _make_api_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送真实 API 请求（使用 requests 库）
        """
        import requests
        
        # 检查 API 密钥是否配置
        if not self.api_key:
            logger.error("API key not configured. Please set up in Settings.")
            return {
                "success": False,
                "message": "API 密钥未配置，请在设置中配置 API Key",
                "timestamp": datetime.now().isoformat()
            }
        
        try:
            code_text = context.get("text", "")
            selected_code = context.get("selection", "")
            language = context.get("language", "python")
            filename = context.get("filename", "Untitled.py")
            mode = context.get("mode", "analysis")
            prefix = context.get("prefix", "")
            
            # 构建请求
            url = self.endpoint
            if not url.endswith('/chat/completions'):
                url = url.rstrip('/') + '/chat/completions'
            
            # 补全模式：智能提示
            if mode == "completion":
                # 分析代码上下文
                lines = prefix.split('\n') if prefix else []
                current_line = lines[-1] if lines else ""
                current_line_stripped = current_line.strip()
                
                # 获取前面几行作为上下文
                context_lines = lines[-20:] if len(lines) > 20 else lines
                context_code = '\n'.join(context_lines)
                
                # 智能 System Prompt
                system_prompt = """You are an expert Python code completion AI, similar to GitHub Copilot.

Your task: Complete the code naturally and intelligently.

STRICT OUTPUT RULES:
1. Output ONLY the code completion - no explanations, no markdown, no code blocks
2. The completion should seamlessly continue from where the cursor is
3. Match the existing code style, indentation, and naming conventions
4. Be smart about what to complete:
   - For function definitions: complete parameters, docstring, and body
   - For loops/conditions: complete the block with sensible logic
   - For class definitions: add __init__ and common methods
   - For incomplete statements: finish them logically

EXAMPLES of good completions:

Input: "def calculate_sum"
Output: (numbers):
    \"\"\"Calculate the sum of a list of numbers.\"\"\"
    return sum(numbers)

Input: "for i in range"
Output: (10):
        print(i)

Input: "class User"
Output: :
    \"\"\"A class representing a user.\"\"\"
    
    def __init__(self, name, email):
        self.name = name
        self.email = email

Input: "if x > "
Output: 0:
        print("Positive")

Remember: Output ONLY the completion code, nothing else."""

                # 智能 User Prompt
                user_prompt = f"""Complete this Python code. Output ONLY the completion that should come after the cursor position (marked with |).

```python
{context_code}|
```

The cursor is at the end of: `{current_line_stripped}`

Complete it naturally:"""
                
                temperature = 0.3  # 稍微提高以增加创造性
                max_tokens = 300   # 增加 token 数以支持更长的补全
            else:
                system_prompt = "You are a helpful code analysis assistant."
                user_prompt = self._build_prompt(context)
                temperature = 0.7
                max_tokens = 2000
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            logger.info(f"Sending request to {url} (mode={mode})")
            
            # 发送请求（增加超时时间）
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60  # 60秒超时
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 提取响应
            ai_response = ""
            if "choices" in result and len(result["choices"]) > 0:
                ai_response = result["choices"][0].get("message", {}).get("content", "")
            
            if not ai_response:
                raise ValueError("Empty response from AI")
            
            # 清理响应
            ai_response = self._clean_completion(ai_response, mode)
            
            logger.info(f"✅ AI response: {ai_response[:50]}...")
            
            return {
                "success": True,
                "data": {
                    "raw_analysis": ai_response,
                    "metadata": {
                        "filename": filename,
                        "language": language,
                        "mode": mode
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return {
                "success": False,
                "message": "Request timed out. Please try again.",
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {e}")
            return {
                "success": False,
                "message": f"API error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _clean_completion(self, response: str, mode: str) -> str:
        """
        智能清理 AI 补全响应
        移除不需要的格式，保留纯代码
        """
        if mode != "completion":
            return response
        
        text = response.strip()
        
        # 1. 移除 markdown 代码块
        if '```' in text:
            lines = text.split('\n')
            code_lines = []
            in_block = False
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('```'):
                    in_block = not in_block
                    continue
                if in_block:
                    code_lines.append(line)
                elif not any(stripped.startswith(x) for x in ['```', 'Here', 'This', 'The ']):
                    # 不在代码块内但看起来像代码的行
                    if stripped and (stripped[0] in '()[]{}#\'"' or 
                                    stripped.startswith(('def ', 'class ', 'if ', 'for ', 
                                                        'while ', 'return ', 'import ', 'from '))):
                        code_lines.append(line)
            if code_lines:
                text = '\n'.join(code_lines)
        
        # 2. 移除解释性文字
        lines = text.split('\n')
        result_lines = []
        skip_until_code = True
        
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            
            # 跳过解释性开头
            if skip_until_code:
                # 检测代码开始的标志
                if (stripped.startswith(('(', ')', '[', ']', '{', '}', ':', '#', '"', "'")) or
                    stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 
                                        'return ', 'import ', 'from ', 'try', 'with ',
                                        'elif ', 'else:', 'except', 'finally:', 'async ',
                                        'self.', 'print(', 'raise ', 'yield ', 'pass',
                                        '    ', '\t')) or  # 缩进的代码
                    (len(stripped) > 0 and stripped[0].isalpha() and '=' in stripped)):  # 赋值语句
                    skip_until_code = False
                elif any(x in lower for x in ['here', 'this is', 'the code', 'complete', 
                                              'output:', 'result:', 'answer:', 'following']):
                    continue
                else:
                    skip_until_code = False
            
            if not skip_until_code:
                result_lines.append(line)
        
        result = '\n'.join(result_lines).strip()
        
        # 3. 移除末尾的解释
        if result:
            final_lines = result.split('\n')
            while final_lines:
                last = final_lines[-1].strip().lower()
                if (not last or 
                    last.startswith(('this ', 'note:', 'explanation:', 'the above'))):
                    final_lines.pop()
                else:
                    break
            result = '\n'.join(final_lines)
        
        return result.rstrip() if result else text.strip()

    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建发送给 AI 的提示词
        
        Args:
            context: 上下文字典
        
        Returns:
            构建好的提示词
        """
        code_text = context.get("text", "")
        selected_code = context.get("selection", "")
        language = context.get("language", "python")
        filename = context.get("filename", "Untitled.py")
        mode = context.get("mode", "analysis")
        prefix = context.get("prefix", "")
        suffix = context.get("suffix", "")
        
        if mode == "completion":
            # 补全模式：请求代码补全
            prompt = f"""You are a code completion assistant for {language}.
Given the code context, provide a natural and useful code completion.

File: {filename}
Language: {language}

Code before cursor:
```{language}
{prefix[-2000:] if len(prefix) > 2000 else prefix}
```

Code after cursor:
```{language}
{suffix[:500] if len(suffix) > 500 else suffix}
```

Provide ONLY the code to insert at the cursor position. Do not include any explanation.
The completion should:
1. Be syntactically correct
2. Follow the existing code style
3. Be concise and useful
4. Maintain proper indentation

Respond with only the code completion, nothing else."""
        else:
            # 分析模式
            prompt = f"""请分析以下 {language} 代码：

文件名: {filename}

代码:
```{language}
{code_text}
```"""

            if selected_code:
                prompt += f"""

选中的代码片段:
```{language}
{selected_code}
```"""

            prompt += """

请提供以下分析：
1. 代码功能和目的
2. 潜在的bug或问题
3. 代码质量和最佳实践建议
4. 可能的改进方案
5. 性能优化建议（如果适用）

请用中文回答。"""
        
        return prompt

    def _create_ui_result(self, ai_response: str, original_code: str, language: str, filename: str) -> str:
        """
        生成 HTML 格式的 UI 结果
        
        Args:
            ai_response: AI 分析结果文本
            original_code: 原始代码
            language: 编程语言
            filename: 文件名
        
        Returns:
            HTML 格式的字符串
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Code Analysis - {filename}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .metadata {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .metadata-item {{
            margin: 5px 0;
        }}
        .analysis {{
            margin-top: 20px;
            line-height: 1.6;
            white-space: pre-wrap;
        }}
        .code-block {{
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
            margin: 10px 0;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Code Analysis Report</h1>
        
        <div class="metadata">
            <div class="metadata-item"><strong>File:</strong> {filename}</div>
            <div class="metadata-item"><strong>Language:</strong> {language}</div>
            <div class="metadata-item"><strong>Code Length:</strong> {len(original_code)} characters</div>
        </div>
        
        <div class="analysis">
            <h2>Analysis Result</h2>
            <div class="code-block">
{self._escape_html(ai_response)}
            </div>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _create_error_ui(self, error_msg: str) -> str:
        """
        生成错误提示的 HTML 界面
        
        Args:
            error_msg: 错误消息
        
        Returns:
            HTML 格式的错误页面
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Analysis Error</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .error-container {{
            background-color: #ffebee;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #f44336;
        }}
        h1 {{
            color: #c62828;
        }}
        .error-message {{
            color: #d32f2f;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>❌ Error</h1>
        <div class="error-message">
            {self._escape_html(error_msg)}
        </div>
    </div>
</body>
</html>
"""
        return html

    def _escape_html(self, text: str) -> str:
        """转义 HTML 特殊字符"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;"))

    def on_suggestion_accepted(self, suggestion: str):
        """当用户接受建议时的回调（用于实时补全功能）"""
        logger.info(f"Suggestion accepted: {suggestion[:50]}...")

    def on_suggestion_rejected(self, suggestion: str):
        """当用户拒绝建议时的回调（用于实时补全功能）"""
        logger.info(f"Suggestion rejected: {suggestion[:50]}...")

    def get_suggestion_metadata(self, analysis_result):
        """
        从AI分析结果中提取元数据

        Args:
            analysis_result: AI分析返回的结果字典

        Returns:
            包含元数据的字典
        """
        try:
            if analysis_result.get("success", False):
                metadata = analysis_result["data"]["metadata"]
                return {
                    "success": True,
                    "filename": metadata.get("filename", "N/A"),
                    "language": metadata.get("language", "python"),
                    "code_length": metadata.get("code_length", 0),
                    "analysis_length": len(analysis_result["data"]["raw_analysis"]),
                    "timestamp": analysis_result.get("timestamp", "")
                }
        except Exception as e:
            print(f"提取元数据时出错: {e}")

        # 如果失败或没有元数据，返回默认值
        return {
            "success": False,
            "error": "无法提取元数据",
            "filename": "Unknown",
            "language": "python",
            "code_length": 0,
            "analysis_length": 0
        }

