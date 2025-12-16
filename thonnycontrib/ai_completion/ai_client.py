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
            # 从 settings 模块加载配置
            from .settings import get_ai_config
            config = get_ai_config()
            
            if not self.api_key:
                self.api_key = config.get("api_key")
            if not self.endpoint or self.endpoint == "https://api.example.com/v1/chat/completions":
                self.endpoint = config.get("endpoint", self.endpoint)
            if not self.model or self.model == "gpt-3.5-turbo":
                self.model = config.get("model", self.model)
            
            logger.debug(f"Loaded config: endpoint={self.endpoint}, model={self.model}")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    def request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送代码分析请求到 AI 服务
        
        Args:
            context: 包含以下键的字典：
                - text: 完整代码文本
                - selection: 选中的代码（如果有）
                - language: 编程语言
                - filename: 文件名
        
        Returns:
            包含以下键的字典：
                - success: 是否成功
                - data: 结果数据（如果成功）
                    - raw_analysis: AI 分析结果文本
                    - metadata: 元数据
                    - ui_html: HTML 格式的 UI（可选）
                - timestamp: 时间戳
                - message: 错误消息（如果失败）
        """
        try:
            # 提取上下文信息
            code_text = context.get("text", "")
            selected_code = context.get("selection", "")
            language = context.get("language", "python")
            filename = context.get("filename", "Untitled.py")
            
            logger.info(f"Requesting AI analysis for {filename} ({language})")
            
            # 检查是否有 API 密钥
            if not self.api_key or self.api_key == "placeholder-key-12345":
                # 使用模拟模式（用于测试）
                return self._simulate_request(context)
            
            # 真实 API 调用
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
        
        # 生成模拟的分析结果
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
            "line_count": len(code_text.splitlines())
        }
        
        return {
            "success": True,
            "data": {
                "raw_analysis": analysis_text,
                "metadata": metadata,
                "ui_html": self._create_ui_result(analysis_text, code_text, language, filename)
            },
            "timestamp": datetime.now().isoformat()
        }

    def _make_api_request(self, context: Dict[str, Any]) -> Dict[str, Any]:

        try:
            import requests
            
            code_text = context.get("text", "")
            selected_code = context.get("selection", "")
            language = context.get("language", "python")
            filename = context.get("filename", "Untitled.py")
            
            # 构建请求数据
            prompt = self._build_prompt(code_text, selected_code, language, filename)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful code analysis assistant. Analyze the provided code and provide detailed feedback, suggestions, and improvements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            # 发送请求
            logger.info(f"Sending request to {self.endpoint}")
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # 检查响应
            response.raise_for_status()
            result = response.json()
            
            # 提取 AI 响应
            ai_response = ""
            if "choices" in result and len(result["choices"]) > 0:
                ai_response = result["choices"][0].get("message", {}).get("content", "")
            
            if not ai_response:
                raise ValueError("Empty response from AI service")
            
            # 构建返回结果
            metadata = {
                "filename": filename,
                "language": language,
                "code_length": len(code_text),
                "selection_length": len(selected_code),
                "line_count": len(code_text.splitlines())
            }
            
            return {
                "success": True,
                "data": {
                    "raw_analysis": ai_response,
                    "metadata": metadata,
                    "ui_html": self._create_ui_result(ai_response, code_text, language, filename)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except ImportError:
            logger.error("requests library not available")
            return {
                "success": False,
                "message": "requests library is required for API calls. Please install it: pip install requests",
                "timestamp": datetime.now().isoformat()
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {
                "success": False,
                "message": f"API request failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def _build_prompt(self, code_text: str, selected_code: str, language: str, filename: str) -> str:
        """
        构建发送给 AI 的提示词
        
        Args:
            code_text: 完整代码
            selected_code: 选中的代码
            language: 编程语言
            filename: 文件名
        
        Returns:
            构建好的提示词
        """
        prompt = f"""请分析以下 {language} 代码：

文件名: {filename}

完整代码:
```
{code_text}
"""

        if selected_code:
            prompt += f"""
选中的代码片段:
```
{selected_code}
```
"""

        prompt += """
请提供以下分析：
1. 代码功能和目的
2. 潜在的bug或问题
3. 代码质量和最佳实践建议
4. 可能的改进方案
5. 性能优化建议（如果适用）

请用中文回答。
"""
        
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

