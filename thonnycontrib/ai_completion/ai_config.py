# ai_config.py
"""
AI Completion Configuration Module - Sprint 3
管理 AI 补全助手的配置，包括：
- 启用/禁用开关
- API 设置
- 快捷键配置
- 上下文窗口设置
"""
import json
import os
from logging import getLogger

logger = getLogger(__name__)


class AICompletionConfig:
    """AI补全配置管理器"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        "general": {
            "enabled": True,  # 是否启用 AI 助手
            "show_notifications": True,  # 是否显示通知
            "auto_trigger": False,  # 是否自动触发（输入时）
            "language": "zh"  # 界面语言
        },
        "shortcuts": {
            "trigger_ai": "Control-Alt-a",
            "accept_suggestion": ["Tab"],
            "reject_suggestion": ["Escape"],
            "show_settings": "Control-Shift-a"
        },
        "context": {
            "lines_before": 50,  # 光标前的行数
            "lines_after": 10,   # 光标后的行数
            "max_chars": 4000,   # 最大上下文字符数
            "max_file_size": 100000  # 最大文件大小警告阈值
        },
        "completion": {
            "mode": "inline",  # inline 或 popup
            "debounce_ms": 500,  # 防抖延迟
            "min_trigger_interval_ms": 1000,  # 最小触发间隔
            "preserve_indent": True  # 保持缩进
        },
        "ai_service": {
            "enabled": True,
            "provider": "openai_compatible",
            "api_key": "",
            "endpoint": "https://api.microatp.com/v1/chat/completions",
            "model": "deepseek-chat",
            "timeout": 30,
            "max_tokens": 500
        },
        "api_settings": {}  # 向后兼容
    }

    def __init__(self):
        self.config_file = self._get_config_path()
        self.config = self._load_config()
        logger.info(f"AICompletionConfig initialized from {self.config_file}")

    def _get_config_path(self):
        """获取配置文件路径"""
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'Thonny', 'ai_completion')
        else:  # Linux/macOS
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'Thonny', 'ai_completion')

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def _load_config(self):
        """加载配置"""
        config = self._deep_copy(self.DEFAULT_CONFIG)

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 深度合并配置
                    self._merge_configs(config, user_config)
                logger.info("User configuration loaded successfully")
        except Exception as e:
            logger.warning(f"配置加载错误，使用默认配置: {e}")

        return config
    
    def _deep_copy(self, obj):
        """深拷贝对象"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj

    def _merge_configs(self, default, user):
        """深度合并配置"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_configs(default[key], value)
            else:
                default[key] = value

    # ==================== 通用设置 ====================
    
    def is_enabled(self) -> bool:
        """检查 AI 助手是否启用"""
        return self.config.get("general", {}).get("enabled", True)
    
    def set_enabled(self, enabled: bool):
        """设置 AI 助手启用状态"""
        if "general" not in self.config:
            self.config["general"] = {}
        self.config["general"]["enabled"] = enabled
        logger.info(f"AI Assistant {'enabled' if enabled else 'disabled'}")
    
    def is_auto_trigger(self) -> bool:
        """检查是否自动触发"""
        return self.config.get("general", {}).get("auto_trigger", False)
    
    def set_auto_trigger(self, enabled: bool):
        """设置自动触发"""
        if "general" not in self.config:
            self.config["general"] = {}
        self.config["general"]["auto_trigger"] = enabled

    # ==================== 快捷键设置 ====================
    
    def get_shortcut(self, action: str):
        """获取快捷键"""
        shortcuts = self.config.get("shortcuts", {})

        if action == "trigger_ai":
            return shortcuts.get("trigger_ai", "Control-Alt-a")
        elif action == "accept_suggestion":
            result = shortcuts.get("accept_suggestion", ["Tab"])
            return result if isinstance(result, list) else [result]
        elif action == "reject_suggestion":
            result = shortcuts.get("reject_suggestion", ["Escape"])
            return result if isinstance(result, list) else [result]
        elif action == "show_settings":
            return shortcuts.get("show_settings", "Control-Shift-a")

        return None
    
    def set_shortcut(self, action: str, keys):
        """设置快捷键"""
        if "shortcuts" not in self.config:
            self.config["shortcuts"] = {}
        self.config["shortcuts"][action] = keys

    # ==================== 上下文设置 ====================
    
    def get_context_config(self) -> dict:
        """获取上下文配置"""
        return self.config.get("context", {
            "lines_before": 50,
            "lines_after": 10,
            "max_chars": 4000,
            "max_file_size": 100000
        })
    
    def set_context_config(self, lines_before: int = None, lines_after: int = None, 
                          max_chars: int = None, max_file_size: int = None):
        """设置上下文配置"""
        if "context" not in self.config:
            self.config["context"] = {}
        
        if lines_before is not None:
            self.config["context"]["lines_before"] = lines_before
        if lines_after is not None:
            self.config["context"]["lines_after"] = lines_after
        if max_chars is not None:
            self.config["context"]["max_chars"] = max_chars
        if max_file_size is not None:
            self.config["context"]["max_file_size"] = max_file_size

    # ==================== 补全设置 ====================
    
    def get_completion_config(self) -> dict:
        """获取补全配置"""
        return self.config.get("completion", {
            "mode": "inline",
            "debounce_ms": 500,
            "min_trigger_interval_ms": 1000,
            "preserve_indent": True
        })
    
    def get_debounce_ms(self) -> int:
        """获取防抖延迟"""
        return self.config.get("completion", {}).get("debounce_ms", 500)
    
    def get_min_trigger_interval(self) -> int:
        """获取最小触发间隔"""
        return self.config.get("completion", {}).get("min_trigger_interval_ms", 1000)

    # ==================== AI 服务设置 ====================
    
    def get_ai_service_config(self) -> dict:
        """获取 AI 服务配置"""
        # 首先检查 api_settings（向后兼容）
        api_settings = self.config.get("api_settings", {})
        ai_service = self.config.get("ai_service", {})
        
        # 合并配置，api_settings 优先
        return {
            "enabled": ai_service.get("enabled", True),
            "provider": ai_service.get("provider", "openai_compatible"),
            "api_key": api_settings.get("api_key") or ai_service.get("api_key", ""),
            "endpoint": api_settings.get("endpoint") or ai_service.get("endpoint", 
                       "https://demo.demo.com/v1/"),
            "model": api_settings.get("model") or ai_service.get("model", "deepseek-chat"),
            "timeout": ai_service.get("timeout", 30),
            "max_tokens": ai_service.get("max_tokens", 500)
        }
    
    def set_ai_service_config(self, api_key: str = None, endpoint: str = None, 
                              model: str = None, timeout: int = None, max_tokens: int = None):
        """设置 AI 服务配置"""
        if "ai_service" not in self.config:
            self.config["ai_service"] = {}
        if "api_settings" not in self.config:
            self.config["api_settings"] = {}
        
        if api_key is not None:
            self.config["ai_service"]["api_key"] = api_key
            self.config["api_settings"]["api_key"] = api_key
        if endpoint is not None:
            self.config["ai_service"]["endpoint"] = endpoint
            self.config["api_settings"]["endpoint"] = endpoint
        if model is not None:
            self.config["ai_service"]["model"] = model
            self.config["api_settings"]["model"] = model
        if timeout is not None:
            self.config["ai_service"]["timeout"] = timeout
        if max_tokens is not None:
            self.config["ai_service"]["max_tokens"] = max_tokens

    # ==================== 配置保存/加载 ====================
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False
    
    def reload_config(self):
        """重新加载配置"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.config = self._deep_copy(self.DEFAULT_CONFIG)
        logger.info("Configuration reset to defaults")
    
    def export_config(self) -> str:
        """导出配置为 JSON 字符串"""
        return json.dumps(self.config, indent=2, ensure_ascii=False)
    
    def import_config(self, json_str: str) -> bool:
        """从 JSON 字符串导入配置"""
        try:
            new_config = json.loads(json_str)
            self.config = self._deep_copy(self.DEFAULT_CONFIG)
            self._merge_configs(self.config, new_config)
            return True
        except Exception as e:
            logger.error(f"导入配置失败: {e}")
            return False


# 全局配置实例（单例模式）
_config_instance = None

def get_config() -> AICompletionConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AICompletionConfig()
    return _config_instance


def is_ai_enabled() -> bool:
    """便捷函数：检查 AI 是否启用"""
    return get_config().is_enabled()


def get_ai_config() -> dict:
    """便捷函数：获取 AI 服务配置（向后兼容）"""
    return get_config().get_ai_service_config()
