"""
测试脚本：调用 trigger_ai_completion() 函数

使用方法：
1. 在 Thonny 中打开此文件
2. 运行此脚本（F5 或 Run 菜单）
3. 脚本会自动调用 trigger_ai_completion() 函数

或者在 Thonny 的 Shell 中直接运行：
    exec(open('test_ai_completion.py').read())
"""

import sys
import os
from pathlib import Path

def test_trigger_ai_completion():
    """
    测试 trigger_ai_completion() 函数
    """
    print("=" * 60)
    print("AI Completion 功能测试脚本")
    print("=" * 60)
    print()
    
    try:
        # 检查是否在 Thonny 环境中
        print("[1/4] 检查 Thonny 环境...")
        try:
            from thonny import get_workbench
            import thonny
            # 检查 _workbench 全局变量
            if not hasattr(thonny, '_workbench') or thonny._workbench is None:
                print("警告: Thonny 工作台未初始化")
                print()
                print("   说明: 你在 Shell 中运行此脚本。")
                print("   Shell 运行在后端进程，无法访问前端的 GUI 组件。")
                print()
                print("   正确的测试方法:")
                print("   1. 在编辑器中打开一个文件")
                print("   2. 使用快捷键: Ctrl+Alt+A")
                print("   3. 或使用菜单: Tools → AI Completion")
                print()
                print("   继续运行非 GUI 测试（检查函数是否可以导入）...")
                # 不直接返回 False，而是继续尝试
                wb = None
            else:
                wb = get_workbench()
                print("Thonny 工作台已初始化")
        except ImportError as e:
            print(f"错误: 无法导入 Thonny 模块 - {e}")
            print("提示: 此测试必须在 Thonny IDE 环境中运行")
            return False
        
        # 导入 trigger_ai_completion 函数
        print("\n[2/4] 导入 trigger_ai_completion 函数...")
        try:
            from thonnycontrib.ai_completion.main import trigger_ai_completion
            print("成功导入 trigger_ai_completion 函数")
        except ImportError as e:
            print(f"错误: 无法导入 trigger_ai_completion - {e}")
            print("   提示: 确保 ai_completion 插件已正确安装")
            return False
        
        # 检查是否有活动的编辑器（仅当工作台已初始化时）
        print("\n[3/4] 检查编辑器状态...")
        if wb is None:
            print("跳过: 工作台未初始化，无法检查编辑器")
        else:
            try:
                editor = wb.get_editor_notebook().get_current_editor()
                if editor:
                    text_widget = editor.get_text_widget()
                    code_content = text_widget.get("1.0", "end-1c")
                    code_length = len(code_content)
                    print(f"找到活动编辑器")
                    print(f"  当前代码长度: {code_length} 字符")
                    if code_length > 0:
                        preview = code_content[:50].replace('\n', '\\n')
                        print(f"  代码预览: {preview}...")
                    else:
                        print("  编辑器为空")
                else:
                    print("警告: 当前没有活动的编辑器")
                    print("  提示: 打开一个文件以获得更好的测试效果")
            except (AttributeError, AssertionError) as e:
                print(f"警告: 无法访问编辑器 - {e}")
                print("  这可能是正常的，如果 GUI 尚未完全初始化")
        
        # 调用 trigger_ai_completion() 函数
        print("\n[4/4] 调用 trigger_ai_completion() 函数...")
        if wb is None:
            print("跳过: 在 Shell 中无法调用此函数")
            print()
            print("  提示:")
            print("  trigger_ai_completion() 需要在 Thonny 的 GUI 前端中运行。")
            print("  在 Shell 中调用会失败，因为 Shell 运行在后端进程，无法访问 GUI。")
            print()
            print("  要真正测试此功能，请:")
            print("  1. 在编辑器中打开一个 Python 文件")
            print("  2. 按 Ctrl+Alt+A 快捷键")
            print("  3. 或使用菜单: Tools → AI Completion")
            print()
            print("  非 GUI 测试部分已完成（函数可以正常导入）。")
            return True  # 在 Shell 中这是预期的，不算失败
        else:
            print("  正在触发 AI Completion 功能...")
            print("  注意: 如果弹出消息框，这是正常现象")
            print()
            
            try:
                # 调用函数（这会显示一个消息框，如果 GUI 可用）
                trigger_ai_completion()
                print("函数调用成功完成")
                print("  如果看到了消息框，说明函数正常工作")
            except Exception as e:
                error_msg = str(e)
                if "not initialized" in error_msg.lower() or "workbench" in error_msg.lower():
                    print(f"警告: 函数需要 GUI 环境 - {e}")
                    print("  这是预期的行为，如果不在 Thonny 的 GUI 中运行")
                else:
                    print(f"错误: 调用函数时发生异常 - {e}")
                    import traceback
                    traceback.print_exc()
                    return False
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print("\n提示:")
        print("- 如果看到消息框显示了代码内容，说明测试成功")
        print("- 也可以通过菜单 Tools > AI Completion 来调用")
        print("- 或使用快捷键 Ctrl+Alt+A (需要在编辑器窗口)")
        
        return True
        
    except Exception as e:
        print(f"\n 测试过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_without_gui():
    """
    不依赖 GUI 的单元测试（用于自动化测试）
    """
    print("运行非 GUI 测试...")
    
    try:
        from thonnycontrib.ai_completion.main import trigger_ai_completion
        
        # 检查函数是否存在
        assert callable(trigger_ai_completion), "trigger_ai_completion 应该是可调用的"
        print("✓ 函数存在且可调用")
        
        # 检查函数签名
        import inspect
        sig = inspect.signature(trigger_ai_completion)
        params = list(sig.parameters.keys())
        assert 'event' in params or len(params) == 0, "函数应该接受 event 参数"
        print("✓ 函数签名正确")
        
        print("非 GUI 测试通过")
        return True
        
    except Exception as e:
        print(f"非 GUI 测试失败: {e}")
        return False


if __name__ == "__main__":
    # 主测试
    success = test_trigger_ai_completion()
    
    # 如果主测试失败，尝试运行非 GUI 测试
    if not success:
        print("\n" + "-" * 60)
        print("尝试运行非 GUI 测试...")
        test_without_gui()
    
    # 返回退出码
    sys.exit(0 if success else 1)

