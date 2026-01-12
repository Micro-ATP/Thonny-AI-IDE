"""
AI Code Completion Plugin - Copilot Style
Ghost Text 实现 - 简单稳健版
"""
from thonny import get_workbench
from tkinter.messagebox import showinfo
import tkinter as tk
import tkinter.font as tkfont
import os
import threading
from logging import getLogger

logger = getLogger(__name__)

# ==================== 模块导入 ====================
try:
    from . import settings
    HAS_SETTINGS = True
except ImportError:
    HAS_SETTINGS = False

try:
    from .ai_client import AIClient
    HAS_AI_CLIENT = True
except ImportError as e:
    HAS_AI_CLIENT = False
    logger.warning(f"AI client not found: {e}")

try:
    from .ai_config import get_config, is_ai_enabled
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False
    def is_ai_enabled(): return True
    def get_config(): return None

try:
    from .completion_handler import get_smart_context
    HAS_COMPLETION_HANDLER = True
except ImportError:
    HAS_COMPLETION_HANDLER = False

# ========== （导入 ask_ai 模块）==========
try:
    from .ask_ai import open_ask_ai_dialog
    HAS_ASK_AI = True
except ImportError:
    HAS_ASK_AI = False

# ==================== 配置 ====================
AUTO_TRIGGER_ENABLED = True
AUTO_TRIGGER_DELAY_MS = 600
MIN_PREFIX_LENGTH = 4


# ==================== Ghost Text 实现 ====================
class GhostText:
    """
    简单稳健的 Ghost Text 实现
    核心原则：使用 Mark 精确定位，使用 after_idle 确保时序正确
    """
    
    def __init__(self, text_widget: tk.Text):
        self.widget = text_widget
        self.active = False
        self.ghost_text = ""
        
        # 创建样式
        try:
            base_font = tkfont.nametofont("TkFixedFont").actual()
            ghost_font = (base_font["family"], base_font["size"], "italic")
        except:
            ghost_font = ("Courier", 10, "italic")
        
        self.widget.tag_configure("ghost", foreground="#999999", font=ghost_font)
        
        # 创建 marks（gravity 设为 LEFT，这样当在 mark 位置插入文字时，mark 不会移动）
        self.widget.mark_set("ghost_start", "1.0")
        self.widget.mark_gravity("ghost_start", "left")
        self.widget.mark_set("ghost_end", "1.0")
        self.widget.mark_gravity("ghost_end", "left")
        
        self._bind_events()
    
    def _bind_events(self):
        """绑定必要的事件"""
        # Tab: 接受补全 (add=False 抢占优先级)
        self.widget.bind("<Tab>", self._on_tab, add=False)
        
        # Escape: 取消补全
        self.widget.bind("<Escape>", self._on_escape, add=True)
        
        # 鼠标点击: 取消补全
        self.widget.bind("<Button-1>", self._on_interrupt, add=True)
        
        # 任意按键释放: 检查是否需要取消（在键入完成后检查）
        self.widget.bind("<KeyRelease>", self._on_key_release, add=True)
    
    def _on_tab(self, event):
        """Tab 键处理：有补全时接受，无补全时正常缩进"""
        if self.active:
            self._accept()
            return "break"
        
        # 没有活跃补全时，执行正常的 Tab 缩进（Thonny 默认是 4 空格）
        try:
            # 检查是否有选中文本
            try:
                sel_start = self.widget.index("sel.first")
                sel_end = self.widget.index("sel.last")
                # 有选中文本，对每行添加缩进
                start_line = int(sel_start.split('.')[0])
                end_line = int(sel_end.split('.')[0])
                for line in range(start_line, end_line + 1):
                    self.widget.insert(f"{line}.0", "    ")
            except tk.TclError:
                # 没有选中文本，插入 4 个空格
                self.widget.insert("insert", "    ")
        except Exception as e:
            logger.error(f"Tab indent error: {e}")
            self.widget.insert("insert", "    ")
        
        return "break"
    
    def _on_escape(self, event):
        """Escape 键处理"""
        if self.active:
            self._clear()
            return "break"
        return None
    
    def _on_interrupt(self, event):
        """鼠标点击等中断操作"""
        if self.active:
            # 使用 after_idle 确保在事件处理完成后清除
            self.widget.after_idle(self._clear)
        return None
    
    def _on_key_release(self, event):
        """按键释放后检查"""
        # 忽略特殊键
        if event.keysym in ('Tab', 'Escape', 'Shift_L', 'Shift_R', 
                           'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
                           'Caps_Lock', 'Num_Lock'):
            return None
        
        if self.active:
            # 任何其他按键都会取消补全
            self.widget.after_idle(self._clear)
        return None
    
    def show(self, text: str) -> bool:
        """显示补全建议"""
        # 先清除旧的
        self._clear()
        
        if not text or not text.strip():
            return False
        
        try:
            # 获取当前光标位置
            cursor_pos = self.widget.index("insert")
            
            # 设置起始 mark
            self.widget.mark_set("ghost_start", cursor_pos)
            
            # 插入带标签的文本
            self.widget.insert(cursor_pos, text, ("ghost",))
            
            # 设置结束 mark（在插入的文本之后）
            self.widget.mark_set("ghost_end", f"{cursor_pos}+{len(text)}c")
            
            # 把光标移回原位（用户看到的是光标在建议文本之前）
            self.widget.mark_set("insert", cursor_pos)
            
            self.ghost_text = text
            self.active = True
            
            logger.info(f"Ghost text shown: {len(text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Show error: {e}")
            self._clear()
            return False
    
    def _accept(self):
        """接受补全：保留文本，移除标签，光标移到末尾"""
        if not self.active:
            return
        
        try:
            start = self.widget.index("ghost_start")
            end = self.widget.index("ghost_end")
            
            # 移除 tag（保留文本）
            self.widget.tag_remove("ghost", start, end)
            
            # 光标移到末尾
            self.widget.mark_set("insert", end)
            
            logger.info("Ghost text accepted")
            get_workbench().set_status_message("✅ Completion Completed")
            self.widget.after(1500, lambda: get_workbench().set_status_message(""))
            
        except Exception as e:
            logger.error(f"Accept error: {e}")
        
        self.active = False
        self.ghost_text = ""
    
    def _clear(self):
        """清除补全：删除 ghost 文本"""
        if not self.active and not self.ghost_text:
            return
        
        try:
            start = self.widget.index("ghost_start")
            end = self.widget.index("ghost_end")
            
            # 比较位置，确保 start < end
            if self.widget.compare(start, "<", end):
                # 物理删除文本
                self.widget.delete(start, end)
                logger.info("Ghost text cleared")
            
        except Exception as e:
            logger.error(f"Clear error: {e}")
        
        self.active = False
        self.ghost_text = ""


# ==================== 全局管理 ====================
_ghost_texts = {}
_is_requesting = False
_request_lock = threading.Lock()
_auto_timer = None
_setup_done = set()


def get_ghost(widget) -> GhostText:
    """获取或创建 GhostText 实例"""
    wid = id(widget)
    if wid not in _ghost_texts:
        _ghost_texts[wid] = GhostText(widget)
    return _ghost_texts[wid]


def setup_widget(widget):
    """初始化编辑器组件"""
    global _setup_done
    wid = id(widget)
    if wid in _setup_done:
        return
    
    get_ghost(widget)
    widget.bind("<KeyRelease>", lambda e: _on_key_release_auto(e, widget), add=True)
    _setup_done.add(wid)


def _on_key_release_auto(event, widget):
    """自动触发逻辑"""
    global _auto_timer
    
    if not AUTO_TRIGGER_ENABLED:
        return
    
    # 忽略特殊键
    if event.keysym in ('Tab', 'Escape', 'Return', 'Up', 'Down', 'Left', 'Right',
                        'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                        'Alt_L', 'Alt_R', 'BackSpace', 'Delete'):
        return
    
    # 取消之前的定时器
    if _auto_timer:
        try:
            widget.after_cancel(_auto_timer)
        except:
            pass
    
    # 如果已有补全显示，不重复触发
    ghost = get_ghost(widget)
    if ghost.active:
        return
    
    # 检查是否应该触发
    if _should_trigger(widget):
        _auto_timer = widget.after(AUTO_TRIGGER_DELAY_MS, lambda: do_completion(widget))


def _should_trigger(widget) -> bool:
    """判断是否应该触发补全"""
    try:
        line = widget.get("insert linestart", "insert")
        stripped = line.strip()
        
        # 太短不触发
        if len(stripped) < MIN_PREFIX_LENGTH:
            # 除非是特殊结尾
            if not line.rstrip().endswith((':', '=', '(', '[', '{', ',')):
                return False
        
        # 关键字触发
        triggers = ['def ', 'class ', 'for ', 'while ', 'if ', 'elif ', 'with ', 
                   'import ', 'from ', 'return ', 'print(', 'self.']
        if any(stripped.startswith(t) for t in triggers):
            return True
        
        # 特殊字符结尾触发
        if line.rstrip().endswith(('=', '(', '[', '{', ',', ':', '.')):
            return True
        
        # 一定长度后空格触发
        if len(stripped) >= MIN_PREFIX_LENGTH and line.endswith(' '):
            return True
        
        return False
    except:
        return False


def do_completion(widget, manual=False):
    """执行补全请求"""
    global _is_requesting
    
    with _request_lock:
        if _is_requesting:
            return
        _is_requesting = True
    
    try:
        get_workbench().set_status_message("🤖 AI is thinking...")
    except:
        pass
    
    try:
        # 获取上下文
        if HAS_COMPLETION_HANDLER:
            ctx = get_smart_context(widget)
            prefix = ctx.get("prefix", "")
            suffix = ctx.get("suffix", "")
        else:
            prefix = widget.get("1.0", "insert")
            suffix = widget.get("insert", "end-1c")
        
        # 检查长度
        if not manual and len(prefix.strip()) < MIN_PREFIX_LENGTH:
            with _request_lock:
                _is_requesting = False
            get_workbench().set_status_message("")
            return
        
        # 构建请求
        client = AIClient()
        context = {
            "text": prefix + suffix,
            "prefix": prefix,
            "suffix": suffix,
            "language": "python",
            "mode": "completion"
        }
        
        def request_thread():
            global _is_requesting
            try:
                result = client.request(context)
                widget.after(0, lambda: _handle_result(result, widget))
            except Exception as e:
                logger.error(f"Request error: {e}")
            finally:
                with _request_lock:
                    _is_requesting = False
        
        threading.Thread(target=request_thread, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Completion error: {e}")
        with _request_lock:
            _is_requesting = False


def _handle_result(result: dict, widget):
    """处理 AI 返回结果"""
    try:
        get_workbench().set_status_message("")
    except:
        pass
    
    if not result.get("success"):
        return
    
    suggestion = result.get("data", {}).get("raw_analysis", "")
    if suggestion and suggestion.strip():
        get_ghost(widget).show(suggestion)


def trigger_ai_completion(event=None):
    """手动触发补全"""
    try:
        editor = get_workbench().get_editor_notebook().get_current_editor()
        if not editor:
            return "break"
        
        widget = editor.get_text_widget()
        setup_widget(widget)
        
        # 清除旧的再请求
        get_ghost(widget)._clear()
        do_completion(widget, manual=True)
        
    except Exception as e:
        logger.error(f"Trigger error: {e}")
    
    return "break"


# ========== 新函数 ==========
def open_ask_ai_everything(event=None):
    """打开 Ask AI Everything 对话框"""
    try:
        if HAS_ASK_AI:
            open_ask_ai_dialog()
        else:
            # 备用：简单对话框
            _create_simple_ask_dialog()
    except Exception as e:
        from tkinter.messagebox import showerror
        showerror("错误", f"无法打开 AI 对话框:\n\n{e}")
    return "break"


def _create_simple_ask_dialog():
    """简单的 Ask AI 对话框（当 ask_ai.py 不可用时的备用方案）"""
    from tkinter import scrolledtext
    from tkinter.messagebox import showerror

    wb = get_workbench()

    dialog = tk.Toplevel(wb)
    dialog.title("🤖 Ask AI Everything")
    dialog.geometry("600x500")
    dialog.transient(wb)

    main_frame = tk.Frame(dialog, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title = tk.Label(main_frame, text="🤖 Ask AI Everything", font=("Arial", 14, "bold"))
    title.pack(pady=(0, 10))

    chat_frame = tk.LabelFrame(main_frame, text="对话")
    chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED,
                                             bg="#1e1e1e", fg="#ffffff", font=("Consolas", 10))
    chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    input_frame = tk.Frame(main_frame)
    input_frame.pack(fill=tk.X)

    input_text = tk.Text(input_frame, height=3, font=("Arial", 10))
    input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
    input_text.focus_set()

    status_var = tk.StringVar(value="就绪")
    status_label = tk.Label(main_frame, textvariable=status_var, fg="gray")
    status_label.pack(pady=(5, 0))

    def append_message(role, text):
        chat_display.config(state=tk.NORMAL)
        if role == "user":
            chat_display.insert(tk.END, f"\n你: {text}\n")
        elif role == "ai":
            chat_display.insert(tk.END, f"\nAI: {text}\n")
        elif role == "error":
            chat_display.insert(tk.END, f"\n❌ 错误: {text}\n")
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)

    def send_message():
        message = input_text.get("1.0", tk.END).strip()
        if not message:
            return

        input_text.delete("1.0", tk.END)
        append_message("user", message)
        status_var.set("🤔 AI 正在思考...")

        def request_thread():
            try:
                if not HAS_AI_CLIENT:
                    dialog.after(0, lambda: append_message("error", "AI 客户端未加载"))
                    return

                client = AIClient()
                # 使用 request_chat 方法（需要 ai_client.py 支持）
                if hasattr(client, 'request_chat'):
                    result = client.request_chat({"message": message, "history": []})
                else:
                    # 兼容旧版 ai_client.py
                    result = client.request({
                        "text": message,
                        "prefix": message,
                        "suffix": "",
                        "language": "general",
                        "mode": "chat"
                    })

                def handle_result():
                    if result.get("success"):
                        response = result.get("data", {}).get("raw_analysis", "")
                        append_message("ai", response if response else "（无响应）")
                        status_var.set("✅ 完成")
                    else:
                        append_message("error", result.get("message", "未知错误"))
                        status_var.set("❌ 失败")

                dialog.after(0, handle_result)
            except Exception as e:
                dialog.after(0, lambda: append_message("error", str(e)))
                dialog.after(0, lambda: status_var.set("❌ 错误"))

        threading.Thread(target=request_thread, daemon=True).start()

    send_btn = tk.Button(input_frame, text="发送", command=send_message, width=8)
    send_btn.pack(side=tk.RIGHT)

    def on_enter(event):
        if not (event.state & 0x1):
            send_message()
            return "break"

    input_text.bind("<Return>", on_enter)
    append_message("ai", "Anything I can do to help you？")


# ==========  添加结束 ==========


def open_folder(event=None):
    """打开文件夹功能"""
    from tkinter import filedialog
    
    folder = filedialog.askdirectory(title="choose project file")
    if not folder:
        return
    
    wb = get_workbench()
    
    try:
        wb.show_view("FilesView")
    except:
        pass
    
    try:
        files_view = wb.get_view("FilesView")
        if files_view and hasattr(files_view, 'local_files'):
            files_view.local_files.focus_into(folder)
    except:
        pass
    
    try:
        os.chdir(folder)
    except:
        pass
    
    showinfo("opening projects", f"opened: {folder}")


def load_plugin():
    """加载插件"""
    wb = get_workbench()
    
    # 注册 AI 补全命令
    wb.add_command(
        command_id="ai_completion.trigger",
        menu_name="tools",
        command_label="AI Code Completion",
        handler=trigger_ai_completion,
        default_sequence="<Control-Alt-a>",
        accelerator="Ctrl+Alt+A",
        group=100
    )
    # ========== 👇 添加这段（注册 Ask AI 菜单）==========
    wb.add_command(
        command_id="ai_completion.ask_ai",
        menu_name="tools",
        command_label="Ask AI Everything...",
        handler=open_ask_ai_everything,
        default_sequence="<Control-Alt-q>",
        accelerator="Ctrl+Alt+Q",
        group=101
    )
    # ========== 👆 添加结束 ==========
    # 注册打开文件夹命令
    wb.add_command(
        command_id="open_folder",
        menu_name="file",
        command_label="opening folder ...",
        handler=open_folder,
        default_sequence="<Control-Shift-o>",
        accelerator="Ctrl+Shift+O",
        group=5
    )
    
    # 注册设置菜单
    if HAS_SETTINGS:
        from .settings import register_menu_items
        register_menu_items(wb)
    
    # 监听编辑器切换
    def on_editor_change(event=None):
        try:
            editor = wb.get_editor_notebook().get_current_editor()
            if editor:
                setup_widget(editor.get_text_widget())
        except:
            pass
    
    wb.bind("<<NotebookTabChanged>>", on_editor_change, add=True)
    wb.after(1000, on_editor_change)
    
    logger.info("AI Completion Plugin loaded")


if __name__ == "__main__":
    print("AI Completion Plugin")
