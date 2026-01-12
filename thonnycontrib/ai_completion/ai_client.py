"""
AI 客户端模块
负责与 AI 服务进行交互，发送代码分析请求并处理响应
"""
import json
import re
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

    def request_chat(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送通用聊天请求（Ask AI Everything 使用）

        Args:
             context: 包含以下键的字典：
                - message: 用户消息
                - history: 对话历史（可选）

        Returns:
            包含响应的字典
        """
        import requests

        message = context.get("message", "")
        history = context.get("history", [])

        if not message:
            return {
                "success": False,
                "message": "消息不能为空",
                "timestamp": datetime.now().isoformat()
            }

        # 检查 API 密钥
        if not self.api_key:
            return {
                "success": False,
                "message": "API 密钥未配置，请在 Tools → AI Assistant Settings 中设置",
                "timestamp": datetime.now().isoformat()
            }

        try:
            # 构建请求 URL
            url = self.endpoint
            if not url.endswith('/chat/completions'):
                url = url.rstrip('/') + '/chat/completions'

            # 构建消息列表
            messages = [
                {
                    "role": "system",
                    "content": """你是一个友好、博学的 AI 助手。你可以：
1. 回答各种问题（编程、科学、生活、学习等）
2. 帮助解释概念和提供建议
3. 进行友好的对话
4. 帮助解决问题和提供思路

请用英文回答，回答要简洁清晰、有帮助。如果不确定，请诚实说明。"""
                 }
            ]

            # 添加历史对话（最近6条）
            for msg in history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

            # 添加当前消息
            messages.append({"role": "user", "content": message})

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            logger.info(f"Sending chat request to {url}")

            # 发送请求
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()

            # 提取响应
            ai_response = ""
            if "choices" in result and len(result["choices"]) > 0:
                ai_response = result["choices"][0].get("message", {}).get("content", "")

            if not ai_response:
                raise ValueError("Empty response from AI")

            logger.info(f"✅ Chat response received: {len(ai_response)} chars")

            return {
                "success": True,
                "data": {
                    "raw_analysis": ai_response,
                    "metadata": {"mode": "chat", "model": self.model}
                },
                "timestamp": datetime.now().isoformat()
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "response generating out of time，please try again later",
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = "API Key is invalid，please check settings"
            elif "429" in error_msg:
                error_msg = "Too frequent request，please retry later"
            return {
                "success": False,
                "message": f"网络错误: {error_msg}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"错误: {str(e)}",
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
                
                # 获取更多上下文（增加到 50 行，让 AI 看到更多代码）
                context_lines = lines[-50:] if len(lines) > 50 else lines
                context_code = '\n'.join(context_lines)
                
                # 分析当前行的上下文特征
                has_indent = current_line.startswith((' ', '\t'))
                indent_level = len(current_line) - len(current_line.lstrip())
                is_in_function = any('def ' in l for l in lines[-10:])
                is_in_class = any('class ' in l for l in lines[-10:])
                
                # 智能 System Prompt - 更激进、更智能（类似 Copilot）
                system_prompt = """You are an expert Python code completion AI, exactly like GitHub Copilot.

Your mission: Proactively suggest code completions that help programmers write code faster.

CRITICAL RULES - READ CAREFULLY:
1. Output ONLY the code that should come AFTER the cursor - nothing before the cursor
2. NEVER repeat code that already exists in the context
3. NEVER output complete function/class definitions if they already exist
4. If user types partial identifier (e.g., "fibon"), only complete the remaining part (e.g., "acci(10)")
5. If a function is already defined above, DO NOT redefine it - just complete the call

CORE PRINCIPLES:
1. Be PROACTIVE - suggest completions even for partial inputs
2. Be SMART - understand context, variable names, function definitions, imports
3. Be HELPFUL - complete common patterns, suggest next logical steps
4. Be CONFIDENT - make educated guesses, user can always reject

STRICT OUTPUT RULES:
1. Output ONLY the code completion - no explanations, no markdown, no code blocks, no comments
2. The completion should seamlessly continue from where the cursor is
3. Match the existing code style, indentation, and naming conventions EXACTLY
4. Be context-aware: look at defined functions, variables, classes, imports in the code
5. NEVER duplicate existing code - only complete what's missing

COMPLETION STRATEGIES:

1. PARTIAL IDENTIFIERS - CALLING EXISTING FUNCTIONS:
   - If user types "fibon" and context has "def fibonacci(n):", output "acci(10)" (function CALL, not definition)
   - If user types "user_" and context has "user_name", output "name"
   - For existing functions: complete as a CALL (e.g., "acci(10)"), NOT as a definition (e.g., "acci(n):")
   - Match partial identifiers to defined names in context
   - DO NOT output the full function definition again - only complete the call

2. FUNCTION DEFINITIONS - DEFINING NEW FUNCTIONS:
   - If user types "def calculate_sum", complete the FULL function definition with body
   - Complete parameters based on function name and context
   - Add docstrings when appropriate
   - Suggest complete, useful function bodies
   - Output the ENTIRE function definition (parameters, docstring, body)
   - BUT: If function already exists in context, don't redefine it - complete as a call instead

3. CONTROL FLOW:
   - Complete if/for/while blocks with sensible logic
   - Suggest common patterns (e.g., "for item in" -> "items:")

4. EXPRESSIONS:
   - Complete comparisons, assignments, method calls
   - Suggest common operations based on variable types

5. COMMON PATTERNS:
   - List comprehensions, generator expressions
   - Context managers, exception handling
   - Property decorators, class methods

EXAMPLES (PAY ATTENTION - THESE ARE CRITICAL):

Context: 
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

fibon|
```
Output: acci(10)  (function CALL, complete with arguments)
WRONG: bonacci(n): ... (DO NOT output function definition!)
WRONG: bonacci(n):\n    ... (DO NOT include function body!)
WRONG: bonacci(n): ... def fibonacci(n): ... (DO NOT add multiple functions!)

Context: user_name = "John"
Input: "print(user_n|"
Output: ame)  (complete the variable name)

Context: def calculate_sum exists above
Input: "calc|"
Output: ulate_sum(10)  (function CALL, not definition)
NOT: ulate_sum(numbers): ... (DO NOT redefine the function!)

Input: "def calculate_sum|" (NEW function, not defined yet)
Output: (numbers):
    \"\"\"Calculate the sum of a list of numbers.\"\"\"
    return sum(numbers)
(Complete the FULL function definition with body - this is correct!)

Input: "def hello|" (NEW function)
Output: (name):
    \"\"\"Greet someone.\"\"\"
    print(f\"Hello, {name}!\")
(Complete the FULL function definition - this is what user wants!)

Input: "for item in|"
Output: items:
        print(item)

Input: "if x >|"
Output: 0:
        return True

Remember: 
- Be PROACTIVE but SMART
- Only complete what's missing
- NEVER duplicate existing code
- If function exists, complete the CALL, not the definition"""

                # 智能 User Prompt - 提供更多上下文信息
                # 提取已定义的函数、类、变量名（帮助 AI 匹配）
                defined_names = []
                for line in context_lines:
                    # 提取函数定义
                    if 'def ' in line:
                        match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                        if match:
                            defined_names.append(match.group(1))
                    # 提取类定义
                    if 'class ' in line:
                        match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                        if match:
                            defined_names.append(match.group(1))
                    # 提取变量赋值（简单模式）
                    if '=' in line and not line.strip().startswith('#'):
                        match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=', line)
                        if match:
                            defined_names.append(match.group(1))
                
                defined_names_str = ', '.join(set(defined_names[-20:]))  # 最近 20 个
                
                # 分析当前行是否包含部分标识符
                partial_identifier = None
                if current_line_stripped:
                    # 检查是否是部分标识符（字母开头，可能不完整）
                    match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)$', current_line_stripped)
                    if match:
                        potential_id = match.group(1)
                        # 检查这个标识符是否匹配已定义的名称
                        for name in defined_names:
                            if name.startswith(potential_id) and name != potential_id:
                                partial_identifier = (potential_id, name)
                                break
                
                # 构建更清晰的提示
                context_note = ""
                if partial_identifier:
                    context_note = f"\n⚠️ IMPORTANT: User typed '{partial_identifier[0]}' which matches '{partial_identifier[1]}' in context. Only complete the REMAINING part (e.g., if '{partial_identifier[1]}' is a function, output 'acci(10)' not the full function definition)."
                
                user_prompt = f"""Complete this Python code. Output ONLY the code that should come AFTER the cursor position (marked with |).

Full context (code above cursor):
```python
{context_code}|
```

Current line (cursor at end): `{current_line_stripped}`
Current indentation: {indent_level} spaces
In function: {is_in_function}
In class: {is_in_class}

Defined names in context: {defined_names_str if defined_names_str else 'None'}{context_note}

CRITICAL INSTRUCTIONS (MUST FOLLOW):
1. Look at the context - if a function/class/variable is ALREADY DEFINED, DO NOT redefine it
2. If user typed a partial identifier (like "fibon"), only complete the remaining part (like "acci(10)")
   - DO NOT output the full function definition
   - DO NOT include function body
   - DO NOT add multiple functions
3. Only output what comes AFTER the cursor, never repeat what's before
4. If the function already exists above, complete the CALL, not the definition
5. Output ONLY ONE completion - do not generate multiple functions or multiple completions
6. If completing a partial identifier, output the shortest possible completion (e.g., "acci(10)" not "bonacci(n): ...")

REMEMBER: You are completing code, not writing new functions. Keep it minimal and focused!

Analyze the context and suggest the most likely completion. Be proactive but smart!"""
                
                temperature = 0.4  # 提高创造性，更主动地猜测（类似 Copilot）
                max_tokens = 400   # 增加 token 数以支持更长的补全和多行建议
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
        移除不需要的格式，保留纯代码，避免重复定义
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
        
        # 4. 检测并移除重复的函数/类定义（关键修复）
        # 同时处理一行中包含多个函数定义的情况（如 "return x)def fibonacci(n):"）
        if result:
            lines = result.split('\n')
            cleaned_lines = []
            seen_definitions = set()  # 跟踪已见过的定义
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # 检查一行中是否包含多个函数定义（如 "return x)def fibonacci(n):"）
                if 'def ' in stripped and not stripped.startswith('def '):
                    # 找到第一个 'def ' 的位置
                    def_pos = stripped.find('def ')
                    if def_pos > 0:
                        # 只保留 def 之前的部分
                        line = line[:line.find('def ')]
                        stripped = line.strip()
                        logger.debug(f"Found multiple definitions in one line, truncating: {line[:50]}...")
                
                # 检测函数定义
                if stripped.startswith('def '):
                    # 提取函数名
                    match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                    if match:
                        func_name = match.group(1)
                        # 如果已经见过这个函数定义，跳过整个函数体
                        if func_name in seen_definitions:
                            # 跳过直到下一个顶级定义或文件结束
                            continue
                        seen_definitions.add(func_name)
                
                # 检测类定义
                elif stripped.startswith('class '):
                    match = re.search(r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                    if match:
                        class_name = match.group(1)
                        if class_name in seen_definitions:
                            continue
                        seen_definitions.add(class_name)
                
                cleaned_lines.append(line)
            
            result = '\n'.join(cleaned_lines)
        
        # 5. 智能清理：区分"定义新函数"和"调用已存在函数"
        if result:
            lines = result.split('\n')
            if len(lines) > 1:
                first_line = lines[0].strip()
                
                # 情况1: 第一行是 "def " 开头 - 这是定义新函数，应该保留完整的函数定义
                if first_line.startswith('def '):
                    # 这是定义新函数，保留完整的函数定义（包括函数体）
                    # 但需要移除后续重复的函数定义
                    keep_lines = []
                    in_function = True
                    first_func_name = None
                    
                    # 提取第一个函数名
                    match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', first_line)
                    if match:
                        first_func_name = match.group(1)
                    
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        
                        # 检查是否是新的函数定义
                        if stripped.startswith('def '):
                            match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                            if match:
                                func_name = match.group(1)
                                if func_name == first_func_name and i > 0:
                                    # 重复的函数定义，停止保留
                                    break
                                elif i > 0:
                                    # 新的函数定义，停止保留第一个函数
                                    break
                        
                        # 保留当前行
                        keep_lines.append(line)
                        
                        # 检查是否函数体结束（下一行是顶级定义）
                        if i < len(lines) - 1:
                            next_stripped = lines[i + 1].strip()
                            if next_stripped.startswith('def ') or next_stripped.startswith('class '):
                                # 下一个是顶级定义，当前函数结束
                                if not (line.startswith(('    ', '\t')) or stripped == ''):
                                    # 当前行不是缩进的，函数已结束
                                    pass
                    
                    if keep_lines:
                        result = '\n'.join(keep_lines).strip()
                        logger.debug(f"Keeping complete function definition: {result[:50]}...")
                
                # 情况2: 第一行是部分补全（如 "bonacci(n):"），后面有完整定义
                # 这是调用已存在函数的情况，不应该包含函数定义或函数体
                elif (first_line.endswith(':') and 'def ' not in first_line and 
                      '(' in first_line):
                    # 检查后续行是否包含完整的函数定义（def 关键字）
                    has_full_def = any('def ' in line.strip() for line in lines[1:])
                    if has_full_def:
                        # 这是调用已存在函数，不应该有函数定义
                        # 只保留第一行，但需要转换为函数调用格式（去掉冒号，添加参数）
                        # 如果第一行是 "bonacci(n):"，应该转换为 "bonacci(10)" 或类似
                        if first_line.endswith('):'):
                            # 尝试转换为函数调用
                            # 提取函数名部分
                            match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):', first_line)
                            if match:
                                func_call = match.group(1) + '(10)'  # 简化为带参数的调用
                                result = func_call
                            else:
                                result = lines[0].rstrip(':')  # 去掉冒号
                        else:
                            result = lines[0]
                        logger.debug(f"Removed duplicate function definition, keeping only call: {result}")
                    else:
                        # 检查第一行后面是否跟着函数体（缩进的代码）
                        # 如果是，这是错误的，只保留第一行并转换为调用格式
                        if len(lines) > 1:
                            second_line = lines[1].strip() if lines[1] else ""
                            # 如果第二行是缩进的（函数体），这是错误的
                            if second_line and (second_line.startswith('    ') or second_line.startswith('\t')):
                                # 只保留第一行，转换为函数调用格式
                                if first_line.endswith('):'):
                                    match = re.search(r'([a-zA-Z_][a-zA-Z0-9_]*)\([^)]*\):', first_line)
                                    if match:
                                        result = match.group(1) + '(10)'
                                    else:
                                        result = lines[0].rstrip(':')
                                else:
                                    result = lines[0]
                                logger.debug(f"Removed function body after function call, keeping only: {result}")
                
                # 情况3: 第一行是正常补全（不是 def），但后面跟着多个函数定义
                # 找到第一个 "def " 的位置
                first_def_idx = None
                for i, line in enumerate(lines):
                    if 'def ' in line.strip():
                        first_def_idx = i
                        break
                
                if first_def_idx is not None and first_def_idx > 0:
                    # 如果第一个 def 不在第一行，检查是否需要截断
                    # 如果第一行看起来是函数调用（如 "acci(10)"），保留到第一个 def 之前
                    if (first_line and not first_line.startswith('def ') and 
                        (first_line.endswith(')') or '(' in first_line)):
                        # 只保留第一行到第一个 def 之前的内容（函数调用）
                        result = '\n'.join(lines[:first_def_idx]).strip()
                        logger.debug(f"Function call followed by definitions, keeping only call: {result[:50]}...")
                
                # 情况4: 如果补全包含多个函数定义，保留第一个完整的函数定义
                # 检查是否有重复的函数名
                def_names = []
                first_def_start = None
                first_def_end = None
                
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('def '):
                        match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                        if match:
                            func_name = match.group(1)
                            if func_name in def_names:
                                # 重复的函数定义，第一个函数定义结束在这里
                                if first_def_start is not None and first_def_end is None:
                                    first_def_end = i
                                break
                            def_names.append(func_name)
                            if first_def_start is None:
                                first_def_start = i
                
                # 如果找到了第一个函数定义，保留完整的函数定义（包括函数体）
                if first_def_start is not None:
                    if first_def_end is None:
                        # 没有找到重复，保留到文件结束
                        first_def_end = len(lines)
                    
                    # 保留第一个完整的函数定义
                    if first_def_start == 0:
                        # 第一行就是 def，保留完整的函数定义
                        result = '\n'.join(lines[:first_def_end]).strip()
                        logger.debug(f"Keeping first complete function definition: {result[:50]}...")
                
                # 情况5: 检查是否有多个函数定义（即使函数名不同）
                # 如果第一行是部分补全，后面不应该有任何函数定义
                def_count = sum(1 for line in lines if 'def ' in line.strip())
                if def_count > 1 and first_line and not first_line.startswith('def '):
                    # 第一行不是 def，但后面有多个 def，说明可能是部分补全 + 多个函数定义
                    # 只保留第一行（这是函数调用）
                    if first_line.endswith(':') or '(' in first_line:
                        result = lines[0]
                        logger.debug(f"Multiple functions after partial completion, keeping only first line: {result}")
        
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
            print(f"error in extracting meta data: {e}")

        # 如果失败或没有元数据，返回默认值
        return {
            "success": False,
            "error": "unable to extract meta data",
            "filename": "Unknown",
            "language": "python",
            "code_length": 0,
            "analysis_length": 0
        }

