__version__ = "1.0.0-sprint1"
__author__ = "AI Completion Group 1"
__description__ = "AI-powered code completion for Thonny"

# 导入必要的模块供外部
try:
    from . import settings
    from . import main
    from .ai_client import AIClient
except ImportError as e:
    print(f"Warning: Failed to import some modules: {e}")

def load_plugin():
    try:
        from .main import load_plugin as _load
        _load()

    except Exception as e:
        print(f"❌ AI Completion插件加载失败: {e}")
        import traceback
        traceback.print_exc()
        raise


# 可选：添加插件信息函数（便于调试）
def get_plugin_info():
    """获取插件信息"""
    return {
        "name": "AI Code Completion",
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "modules": ["main", "settings", "ai_client"]
    }


# 测试代码
if __name__ == "__main__":
    print("AI Completion Plugin Module Test")
    print(f"Version: {__version__}")
    print(f"Author: {__author__}")

    # 测试导入
    try:
        from .main import trigger_ai_completion

        print("✓ Main module import successful")
    except:
        print("✗ Main module import failed")

    try:
        from . import settings

        print("✓ Settings module import successful")
    except:
        print("✗ Settings module import failed")

    try:
        from .ai_client import AIClient

        print("✓ AI Client import successful")
    except:
        print("✗ AI Client import failed")
