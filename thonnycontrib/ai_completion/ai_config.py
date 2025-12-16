# ai_config.py
import json
import os


class AICompletionConfig:
    """AI补全配置"""

    def __init__(self):
        self.config_file = self._get_config_path()
        self.config = self._load_config()

    def _get_config_path(self):
        """获取配置文件路径"""
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA'), 'Thonny', 'ai_completion')
        else:  # Linux/macOS
            config_dir = os.path.join(os.path.expanduser('~'), '.config', 'Thonny', 'ai_completion')

        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    def _load_config(self):
        """加载配置"""
        default_config = {
            "shortcuts": {
                "trigger_ai": "Control-Alt-a",
                "accept_suggestion": ["Return", "KP_Enter", "Tab"],
                "reject_suggestion": ["Escape", "Control-g"]
            },
            "ai_service": {
                "enabled": True,
                "provider": "simulated",
                "api_key": "",
                "model": "gpt-3.5-turbo"
            }
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    self._merge_configs(default_config, user_config)
        except Exception as e:
            print(f"配置加载错误: {e}")

        return default_config

    def _merge_configs(self, default, user):
        """合并配置"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_configs(default[key], value)
            else:
                default[key] = value

    def get_shortcut(self, action):
        """获取快捷键"""
        shortcuts = self.config.get("shortcuts", {})

        if action == "trigger_ai":
            return shortcuts.get("trigger_ai", "Control-Alt-a")
        elif action == "accept_suggestion":
            result = shortcuts.get("accept_suggestion", ["Return"])
            return result if isinstance(result, list) else [result]
        elif action == "reject_suggestion":
            result = shortcuts.get("reject_suggestion", ["Escape"])
            return result if isinstance(result, list) else [result]

        return None

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False

