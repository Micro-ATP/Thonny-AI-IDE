"""
AI Code Completion Plugin for Thonny
====================================
GitHub Copilot Style AI-powered code completion

Features:
- Ghost Text (灰色建议文本)
- Tab to accept suggestions
- Esc to dismiss
- Smart context window
- Debounce mechanism

Usage:
    Press Ctrl+Alt+A to trigger AI completion
    Press Tab to accept the suggestion
    Press Esc to dismiss

Version: 2.0.0-copilot
"""

__version__ = "2.0.0-copilot"
__author__ = "AI Completion Group 1"
__description__ = "GitHub Copilot style AI code completion for Thonny"

# 导入模块
try:
    from . import settings
    from . import main
    from .ai_client import AIClient
    from .ai_config import get_config, is_ai_enabled
except ImportError as e:
    print(f"Warning: Failed to import some modules: {e}")

# Ghost Text 模块
try:
    from .ghost_text import GhostTextManager, CopilotStyleCompleter
except ImportError as e:
    print(f"Warning: Ghost Text module not available: {e}")


def load_plugin():
    """
    Thonny 插件入口点
    """
    try:
        from .main import load_plugin as _load
        _load()
    except Exception as e:
        print(f"❌ AI Completion plugin failed to load: {e}")
        import traceback
        traceback.print_exc()
        raise


def get_plugin_info():
    """获取插件信息"""
    return {
        "name": "AI Code Completion (Copilot Style)",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "features": [
            "Ghost Text suggestions",
            "Tab to accept",
            "Smart context window",
            "Debounce mechanism",
            "Edge case handling"
        ],
        "shortcuts": {
            "trigger": "Ctrl+Alt+A",
            "accept": "Tab",
            "dismiss": "Esc"
        }
    }


# 测试
if __name__ == "__main__":
    info = get_plugin_info()
    print(f"🤖 {info['name']} v{info['version']}")
    print(f"   {info['description']}")
    print(f"\n📌 Shortcuts:")
    for action, key in info['shortcuts'].items():
        print(f"   {action}: {key}")
