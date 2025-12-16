from thonny import get_workbench
from tkinter.messagebox import showinfo
import os
from logging import getLogger

logger = getLogger(__name__)

# 尝试导入设置模块
try:
    from . import settings
    HAS_SETTINGS = True
    logger.info("Settings module found")
except ImportError as e:
    HAS_SETTINGS = False
    logger.warning(f"Settings module not found: {e}")

# 尝试导入AI客户端（使用相对导入）
try:
    from .ai_client import AIClient
    HAS_AI_CLIENT = True
    logger.info("AI client module found")
except ImportError as e:
    HAS_AI_CLIENT = False
    logger.warning(f"AI client module not found: {e}")


def trigger_ai_completion(event=None):
    """
    触发 AI Completion 功能。
    event 参数是为了快捷键绑定时传入。
    """
    try:
        wb = get_workbench()

        # 检查工作台是否已初始化
        if wb is None:
            showinfo("AI Completion", "Thonny is not ready yet. Please wait for Thonny to fully load.")
            return

        # 检查AI客户端是否可用
        if not HAS_AI_CLIENT:
            showinfo("AI Completion Error",
                    "The AI client module failed to load!\nPlease check if the ai_client.py file exists.")
            return

        try:
            # 尝试获取编辑器笔记本（可能在初始化之前调用）
            editor_notebook = wb.get_editor_notebook()
            editor = editor_notebook.get_current_editor()

            if not editor:
                showinfo("AI Completion", "No active editor! Please open a file first.")
                return

            # 获取文本组件
            text_widget = editor.get_text_widget()

            # 获取完整代码
            full_code = text_widget.get("1.0", "end-1c")

            # 获取选中的代码（如果有）
            try:
                if text_widget.tag_ranges("sel"):
                    selected_code = text_widget.get("sel.first", "sel.last")
                else:
                    selected_code = ""
            except Exception:
                selected_code = ""

            # 获取当前文件名
            current_file = editor.get_filename()
            if current_file:
                filename = os.path.basename(current_file)
                # 根据扩展名判断语言
                if filename.endswith('.py'):
                    language = 'python'
                elif filename.endswith('.js'):
                    language = 'javascript'
                elif filename.endswith('.html'):
                    language = 'html'
                elif filename.endswith('.css'):
                    language = 'css'
                elif filename.endswith('.java'):
                    language = 'java'
                else:
                    language = 'text'
            else:
                filename = "Untitled.py"
                language = 'python'

            # 创建AI客户端实例（会自动从设置加载配置）
            ai_client = AIClient()

            # 准备上下文数据
            context = {
                "text": full_code,
                "selection": selected_code,
                "language": language,
                "filename": filename
            }

            # 显示分析开始消息
            showinfo("AI Analysis", "Starting code analysis...\nPlease wait...")

            # 调用AI分析
            result = ai_client.request(context)

            if result.get("success"):
                # 显示AI分析结果
                raw_analysis = result["data"]["raw_analysis"]

                # 创建结果显示窗口
                from tkinter import Toplevel, Text, Scrollbar, Frame, Button, Label
                from tkinter import VERTICAL, HORIZONTAL, BOTH, END, LEFT, RIGHT, TOP

                # 创建新窗口显示结果
                result_window = Toplevel()
                result_window.title(f"AI Code Analysis Results - {filename}")
                result_window.geometry("800x600")

                # 添加键盘快捷键支持
                def on_accept_key(event=None):
                    accept_suggestion()
                    return "break"

                def on_refuse_key(event=None):
                    refuse_suggestion()
                    return "break"

                def on_close_key(event=None):
                    close_window()
                    return "break"

                # 绑定快捷键
                result_window.bind("<Alt-a>", on_accept_key)  # Alt+A 接受
                result_window.bind("<Alt-r>", on_refuse_key)  # Alt+R 拒绝
                result_window.bind("<Escape>", on_close_key)  # Esc 关闭

                # 创建顶部提示区域
                tip_frame = Frame(result_window, bg="#F0F8FF", height=40)
                tip_frame.pack(fill="x", padx=10, pady=(10, 0))
                tip_frame.pack_propagate(False)  # 保持固定高度

                tip_label = Label(
                    tip_frame,
                    text="快捷键: Alt+A=接受建议 | Alt+R=拒绝建议 | Esc=关闭窗口",
                    bg="#F0F8FF",
                    fg="#2E7D32",
                    font=("Arial", 10)
                )
                tip_label.pack(expand=True)

                # 创建文本框显示分析结果
                text_frame = Frame(result_window)
                text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

                # 添加垂直滚动条
                scrollbar_y = Scrollbar(text_frame)
                scrollbar_y.pack(side="right", fill="y")

                # 添加水平滚动条
                scrollbar_x = Scrollbar(text_frame, orient=HORIZONTAL)
                scrollbar_x.pack(side="bottom", fill="x")

                # 创建文本显示区域
                result_text = Text(
                    text_frame,
                    wrap="word",
                    yscrollcommand=scrollbar_y.set,
                    xscrollcommand=scrollbar_x.set,
                    font=("Courier New", 10)  # 使用等宽字体
                )
                result_text.pack(fill=BOTH, expand=True)

                # 配置滚动条
                scrollbar_y.config(command=result_text.yview)
                scrollbar_x.config(command=result_text.xview)

                # 插入分析结果
                result_text.insert(END, "=" * 60 + "\n")
                result_text.insert(END, "AI Code Analysis Report\n")
                result_text.insert(END, "=" * 60 + "\n\n")

                # 插入元数据
                metadata = result["data"]["metadata"]
                result_text.insert(END, f"Filename: {metadata.get('filename', 'N/A')}\n")
                result_text.insert(END, f"Language: {metadata.get('language', 'N/A')}\n")
                result_text.insert(END, f"Code length: {metadata.get('code_length', 0)} characters\n")
                result_text.insert(END, f"Analysis time: {result.get('timestamp', 'N/A')}\n\n")
                result_text.insert(END, "=" * 60 + "\n\n")

                # 插入AI分析内容
                result_text.insert(END, raw_analysis)

                # 设置为只读
                result_text.config(state="disabled")

                # 创建按钮框架
                button_frame = Frame(result_window)
                button_frame.pack(pady=(0, 10))

                def accept_suggestion():
                    """接受建议按钮的回调函数"""
                    try:
                        # 获取当前编辑器
                        text_widget = editor.get_text_widget()

                        # 获取当前光标位置
                        cursor_pos = text_widget.index("insert")

                        # 插入AI分析结果
                        text_widget.insert(cursor_pos, raw_analysis)

                        # 显示成功消息
                        showinfo("AI 建议",
                                 f"建议已插入到编辑器中！\n\n"
                                 f"插入位置: {cursor_pos}\n"
                                 f"插入长度: {len(raw_analysis)} 字符",
                                 parent=result_window)

                        # 记录到日志
                        logger.info(f"AI suggestion accepted and inserted at {cursor_pos}")

                    except Exception as e:
                        showinfo("错误", f"插入建议时出错: {str(e)}", parent=result_window)
                        logger.error(f"Failed to insert suggestion: {e}")
                    finally:
                        # 关闭结果窗口
                        result_window.destroy()

                def refuse_suggestion():
                    """拒绝建议按钮的回调函数"""
                    # 询问确认
                    from tkinter import messagebox
                    confirm = messagebox.askyesno(
                        "确认拒绝",
                        "确定要拒绝这个AI建议吗？\n\n"
                        "拒绝后将无法恢复。",
                        parent=result_window
                    )

                    if confirm:
                        # 显示拒绝消息
                        showinfo("AI 建议", "建议已被拒绝。", parent=result_window)

                        # 记录到日志
                        logger.info("AI suggestion rejected by user")

                        # 关闭结果窗口
                        result_window.destroy()

                def close_window():
                    """关闭窗口按钮的回调函数"""
                    result_window.destroy()

                # 添加接受按钮
                accept_button = Button(
                    button_frame,
                    text="✓ Accept (Alt+A)",
                    command=accept_suggestion,
                    width=18,
                    height=2,
                    bg="#4CAF50",  # 绿色背景
                    fg="white",  # 白色文字
                    font=("Arial", 10, "bold"),
                    relief="raised",
                    cursor="hand2"
                )
                accept_button.pack(side=LEFT, padx=10)

                # 添加拒绝按钮
                refuse_button = Button(
                    button_frame,
                    text="✗ Refuse (Alt+R)",
                    command=refuse_suggestion,
                    width=18,
                    height=2,
                    bg="#f44336",  # 红色背景
                    fg="white",  # 白色文字
                    font=("Arial", 10, "bold"),
                    relief="raised",
                    cursor="hand2"
                )
                refuse_button.pack(side=LEFT, padx=10)

                # 添加关闭按钮
                close_button = Button(
                    button_frame,
                    text="× Close (Esc)",
                    command=close_window,
                    width=18,
                    height=2,
                    bg="#2196F3",  # 蓝色背景
                    fg="white",  # 白色文字
                    font=("Arial", 10, "bold"),
                    relief="raised",
                    cursor="hand2"
                )
                close_button.pack(side=LEFT, padx=10)

                # 设置窗口焦点
                result_window.focus_set()

                # 居中显示窗口
                result_window.update_idletasks()
                width = result_window.winfo_width()
                height = result_window.winfo_height()
                x = (result_window.winfo_screenwidth() // 2) - (width // 2)
                y = (result_window.winfo_screenheight() // 2) - (height // 2)
                result_window.geometry(f'{width}x{height}+{x}+{y}')

                logger.info("AI analysis complete, result window displayed.")

            else:
                showinfo("AI Analysis Error",
                        f"Analysis failed: {result.get('message', 'Unknown error')}")

        except AssertionError:
            # 编辑器笔记本还未初始化
            showinfo("AI Completion", "Editor not ready yet. Please wait for Thonny to fully load.")
        except AttributeError as e:
            # 编辑器笔记本不存在或属性不存在
            logger.error(f"Editor attribute error: {e}")
            showinfo("AI Completion", f"Editor not available: {str(e)}")
        except RuntimeError as e:
            # 捕获语言服务器相关的错误
            error_msg = str(e)
            if "not initialized" in error_msg.lower() or "hasn't been initialized" in error_msg.lower():
                logger.warning(f"Language server not initialized: {e}")
                showinfo(
                    "AI Completion",
                    "Language server not ready yet.\nPlease wait for Thonny to fully load."
                )
            else:
                logger.error(f"Runtime error: {error_msg}")
                showinfo("AI Completion", f"Runtime error: {error_msg}")
        except Exception as e:
            # 其他错误
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in trigger_ai_completion: {error_details}")
            showinfo("AI Completion Error",
                    f"An error occurred during AI analysis:\n{str(e)}\n\nSee frontend.log for details.")

    except Exception as e:
        # 最外层错误处理（例如 get_workbench 本身失败）
        logger.error(f"Failed to initialize AI completion: {e}")
        import traceback
        logger.error(traceback.format_exc())
        showinfo("AI Completion", f"Failed to initialize: {str(e)}")


def load_plugin():
    """加载插件"""
    wb = get_workbench()
    logger.info("Loading AI Completion plugin...")

    # 注册菜单命令（显示在 Tools 菜单下）
    # 使用 default_sequence 参数自动绑定快捷键
    wb.add_command(
        command_id="ai_completion.trigger",
        menu_name="tools",
        command_label="AI Completion",
        handler=trigger_ai_completion,
        default_sequence="<Control-Alt-a>",  # 快捷键绑定
        accelerator="Ctrl-Alt-A",  # 菜单显示快捷键
        group=100
    )

    # 注册设置菜单
    try:
        if HAS_SETTINGS:
            # 导入settings模块中的register_menu_items函数
            from .settings import register_menu_items

            # 调用函数注册设置菜单
            success = register_menu_items(wb)

            if success:
                logger.info("✅ Settings menu items registered successfully")
            else:
                logger.warning("⚠️ Settings menu registration returned False")
        else:
            logger.warning("⚠️ Settings module not available - skipping menu registration")

    except ImportError as e:
        logger.error(f"❌ Could not import settings module: {e}")
    except Exception as e:
        logger.error(f"❌ Error registering settings menu: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

    # 检查AI客户端状态
    if not HAS_AI_CLIENT:
        logger.warning("AI Completion plugin loaded but ai_client module not found!")
        wb.add_command(
            command_id="ai_completion.error",
            menu_name="tools",
            command_label="AI Completion (Module missing)",
            handler=lambda: showinfo("Error",
                    "AI client module not found!\nPlease ensure that ai_client.py is in the ai_completion directory."),
            group=100
        )
    else:
        logger.info("AI Completion plugin loaded successfully!")


if __name__ == "__main__":
    # 用于测试
    logger.info("AI Completion plugin module loaded")
