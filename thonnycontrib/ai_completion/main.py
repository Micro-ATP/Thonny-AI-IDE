"""
AI Code Completion Plugin - Copilot Style
真正的 AI 自动补全：
- Ghost Text 灰色建议
- Tab 接受
- Esc 取消
- 自动触发
"""
from thonny import get_workbench
from tkinter.messagebox import showinfo
import tkinter as tk
import os
import time
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


# ==================== 配置 ====================
AUTO_TRIGGER_ENABLED = True
AUTO_TRIGGER_DELAY_MS = 600
MIN_PREFIX_LENGTH = 4


# ==================== Ghost Text 实现 ====================
class GhostText:
    """简单可靠的 Ghost Text 实现"""
    
    def __init__(self, text_widget: tk.Text):
        self.widget = text_widget
        self.active = False
        self.suggestion = ""
        self.start_idx = None
        
        # 配置样式
        self.widget.tag_configure("ghost", foreground="#888888")
        
        # 绑定事件（不使用 add=True，直接绑定）
        self._bind_tab()
        self.widget.bind("<Escape>", self._on_escape, add=True)
        self.widget.bind("<Key>", self._on_key, add=True)
    
    def _bind_tab(self):
        """特殊处理 Tab 绑定"""
        # 保存原始 Tab 处理器
        self._orig_tab = self.widget.bind("<Tab>")
        # 替换为我们的处理器
        self.widget.bind("<Tab>", self._on_tab)
    
    def _on_tab(self, event):
        """Tab 键处理"""
        if self.active and self.widget.tag_ranges("ghost"):
            # 有 ghost text，接受它
            self._accept()
            return "break"
        # 没有 ghost text，插入正常的 Tab（4个空格或制表符）
        self.widget.insert("insert", "    ")
        return "break"
    
    def _on_escape(self, event):
        """Esc 键处理"""
        if self.active or self.widget.tag_ranges("ghost"):
            self._clear()
            return "break"
        return None
    
    def _on_key(self, event):
        """其他按键处理"""
        # 忽略修饰键
        if event.keysym in ('Tab', 'Escape', 'Shift_L', 'Shift_R',
                           'Control_L', 'Control_R', 'Alt_L', 'Alt_R'):
            return None
        
        # 如果有 ghost text 且用户输入了字符，清除
        if (self.active or self.widget.tag_ranges("ghost")):
            if event.char and event.char.isprintable():
                self._clear()
        return None
    
    def show(self, text: str) -> bool:
        """显示 ghost text"""
        self._clear()
        
        if not text or not text.strip():
            return False
        
        try:
            self.start_idx = self.widget.index("insert")
            self.suggestion = text
            
            # 插入灰色文本
            self.widget.insert("insert", text, ("ghost",))
            
            # 光标移回起始位置
            self.widget.mark_set("insert", self.start_idx)
            
            self.active = True
            logger.info(f"👻 Shown: {text[:30]}...")
            return True
        except Exception as e:
            logger.error(f"Show error: {e}")
            self._clear()
            return False
    
    def _accept(self):
        """接受 ghost text"""
        if not self.active:
            return
        
        try:
            # 移除灰色标签（文本保留）
            self.widget.tag_remove("ghost", "1.0", "end")
            
            # 找到 ghost text 的实际结束位置
            # 使用 search 而不是字符计数，避免多字节字符问题
            try:
                # 获取当前 ghost text 的结束位置
                ghost_end = self.widget.search(
                    "", self.start_idx, stopindex="end", 
                    regexp=False, nocase=False
                )
                if not ghost_end:
                    # 如果找不到，计算位置
                    ghost_end = self.widget.index(f"{self.start_idx}+{len(self.suggestion)}c")
            except Exception:
                ghost_end = self.widget.index(f"{self.start_idx}+{len(self.suggestion)}c")
            
            # 移动光标到末尾
            self.widget.mark_set("insert", ghost_end if ghost_end else "insert")
            
            logger.info("✅ Accepted")
        except Exception as e:
            logger.error(f"Accept error: {e}")
        
        self._reset()
    
    def _clear(self):
        """清除 ghost text"""
        try:
            # 删除所有 ghost 标签的文本
            while True:
                ranges = self.widget.tag_ranges("ghost")
                if not ranges:
                    break
                self.widget.delete(ranges[0], ranges[1])
        except tk.TclError:
            # widget 可能已被销毁
            pass
        except Exception as e:
            logger.debug(f"Clear error (ignored): {e}")
        self._reset()
    
    def _reset(self):
        """重置状态"""
        self.active = False
        self.suggestion = ""
        self.start_idx = None


# ==================== 全局管理 ====================
_ghost_texts = {}  # widget_id -> GhostText
_is_requesting = False
_request_lock = threading.Lock()
_last_trigger = 0
_auto_timer = None
_setup_done = set()
import weakref
_widget_refs = {}  # widget_id -> weakref


def get_ghost(widget) -> GhostText:
    """获取/创建 GhostText"""
    wid = id(widget)
    
    # 清理已销毁的 widget
    _cleanup_dead_widgets()
    
    if wid not in _ghost_texts:
        _ghost_texts[wid] = GhostText(widget)
        _widget_refs[wid] = weakref.ref(widget)
    return _ghost_texts[wid]


def _cleanup_dead_widgets():
    """清理已销毁的 widget 引用，防止内存泄漏"""
    dead_ids = []
    for wid, ref in _widget_refs.items():
        if ref() is None:  # widget 已被销毁
            dead_ids.append(wid)
    
    for wid in dead_ids:
        _ghost_texts.pop(wid, None)
        _widget_refs.pop(wid, None)
        _setup_done.discard(wid)


def setup_widget(widget):
    """为 widget 设置自动触发"""
    global _setup_done
    wid = id(widget)
    if wid in _setup_done:
        return
    
    # 确保有 GhostText
    get_ghost(widget)
    
    # 绑定自动触发
    widget.bind("<KeyRelease>", lambda e: _on_key_release(e, widget), add=True)
    
    # 绑定销毁事件以清理资源
    widget.bind("<Destroy>", lambda e: _on_widget_destroy(wid), add=True)
    _setup_done.add(wid)


def _on_widget_destroy(wid):
    """widget 销毁时清理资源"""
    _ghost_texts.pop(wid, None)
    _widget_refs.pop(wid, None)
    _setup_done.discard(wid)


def _on_key_release(event, widget):
    """按键释放时检查是否触发"""
    global _auto_timer
    
    if not AUTO_TRIGGER_ENABLED:
        return
    
    # 忽略特殊键
    if event.keysym in ('Tab', 'Escape', 'Return', 'BackSpace', 'Delete',
                       'Up', 'Down', 'Left', 'Right',
                       'Shift_L', 'Shift_R', 'Control_L', 'Control_R'):
        return
    
    # 如果已有建议，不触发
    ghost = _ghost_texts.get(id(widget))
    if ghost and ghost.active:
        return
    
    # 取消之前的定时器
    if _auto_timer:
        try:
            widget.after_cancel(_auto_timer)
        except (tk.TclError, ValueError):
            pass
    
    # 检查是否应该触发
    if _should_trigger(widget):
        _auto_timer = widget.after(AUTO_TRIGGER_DELAY_MS, lambda: do_completion(widget))


def _should_trigger(widget) -> bool:
    """判断是否应该触发"""
    try:
        line = widget.get("insert linestart", "insert").strip()
        if len(line) < MIN_PREFIX_LENGTH:
            return False
        
        triggers = ['def ', 'class ', 'for ', 'while ', 'if ', 'elif ',
                   'with ', 'try:', 'import ', 'from ', 'return ', 'async ']
        for t in triggers:
            if line.startswith(t):
                return True
        return False
    except tk.TclError:
        return False
    except Exception as e:
        logger.debug(f"Trigger check error: {e}")
        return False


def do_completion(widget, manual=False):
    """执行补全"""
    global _is_requesting
    
    with _request_lock:
        if _is_requesting:
            return
        _is_requesting = True
    
    try:
        # 获取上下文
        if HAS_COMPLETION_HANDLER:
            ctx = get_smart_context(widget)
            prefix = ctx.get("prefix", "")
            suffix = ctx.get("suffix", "")
        else:
            prefix = widget.get("1.0", "insert")
            suffix = widget.get("insert", "end-1c")
        
        if len(prefix.strip()) < MIN_PREFIX_LENGTH:
            with _request_lock:
                _is_requesting = False
            return
        
        if not HAS_AI_CLIENT:
            with _request_lock:
                _is_requesting = False
            return
        
        client = AIClient()
        context = {
            "text": prefix + suffix,
            "prefix": prefix,
            "suffix": suffix,
            "language": "python",
            "filename": "code.py",
            "mode": "completion"
        }
        
        # 后台请求
        def request():
            try:
                result = client.request(context)
                widget.after(0, lambda: _handle_result(result, widget))
            except Exception as e:
                logger.error(f"Request error: {e}")
            finally:
                global _is_requesting
                with _request_lock:
                    _is_requesting = False
        
        thread = threading.Thread(target=request, daemon=True)
        thread.start()
        
    except Exception as e:
        logger.error(f"Completion error: {e}")
        with _request_lock:
            _is_requesting = False


def _handle_result(result: dict, widget):
    """处理结果"""
    if not result.get("success"):
        logger.warning(f"AI error: {result.get('message')}")
        return
    
    suggestion = result.get("data", {}).get("raw_analysis", "")
    if not suggestion or not suggestion.strip():
        return
    
    ghost = get_ghost(widget)
    if ghost.show(suggestion):
        logger.info("💡 Tab=接受, Esc=取消")


# ==================== 命令处理 ====================
def trigger_ai_completion(event=None):
    """手动触发 (Ctrl+Alt+A)"""
    global _last_trigger
    
    if HAS_CONFIG and not is_ai_enabled():
        showinfo("AI Completion", "AI Assistant is disabled.")
        return "break"
    
    # 防抖
    now = time.time() * 1000
    if now - _last_trigger < 500:
        return "break"
    _last_trigger = now
    
    try:
        wb = get_workbench()
        if not wb:
            return "break"
        
        editor = wb.get_editor_notebook().get_current_editor()
        if not editor:
            showinfo("AI Completion", "请先打开一个文件！")
            return "break"
        
        widget = editor.get_text_widget()
        setup_widget(widget)
        
        # 清除现有建议
        ghost = get_ghost(widget)
        ghost._clear()
        
        # 执行补全
        do_completion(widget, manual=True)
        
    except Exception as e:
        logger.error(f"Trigger error: {e}")
    
    return "break"


# ==================== 打开文件夹功能 ====================
def open_folder(event=None):
    """打开文件夹（类似 VSCode）"""
    from tkinter import filedialog
    
    folder = filedialog.askdirectory(title="选择项目文件夹")
    if not folder:
        return
    
    wb = get_workbench()
    
    # 1. 显示文件浏览器
    try:
        wb.show_view("FilesView")
    except Exception as e:
        logger.debug(f"Show FilesView error: {e}")
    
    # 2. 导航到选择的文件夹
    try:
        # 获取文件浏览器并设置路径
        files_view = wb.get_view("FilesView")
        if files_view and hasattr(files_view, 'local_files'):
            files_view.local_files.focus_into(folder)
    except Exception as e:
        logger.debug(f"Navigate error: {e}")
    
    # 3. 更改工作目录
    try:
        os.chdir(folder)
        logger.info(f"📂 Working directory: {folder}")
    except OSError as e:
        logger.warning(f"Failed to change working directory: {e}")
    
    # 4. 显示提示
    showinfo("打开文件夹", f"已打开项目文件夹:\n{folder}\n\n工作目录已切换。")


# ==================== 插件加载 ====================
def load_plugin():
    """加载插件"""
    wb = get_workbench()
    logger.info("🚀 Loading AI Completion plugin...")
    
    # AI 补全命令
    wb.add_command(
        command_id="ai_completion.trigger",
        menu_name="tools",
        command_label="AI Code Completion",
        handler=trigger_ai_completion,
        default_sequence="<Control-Alt-a>",
        accelerator="Ctrl+Alt+A",
        group=100
    )
    
    # 打开文件夹命令（类似 VSCode）
    wb.add_command(
        command_id="open_folder",
        menu_name="file",
        command_label="打开文件夹...",
        handler=open_folder,
        default_sequence="<Control-Shift-o>",
        accelerator="Ctrl+Shift+O",
        group=5  # 放在 File 菜单前面
    )
    
    if HAS_SETTINGS:
        try:
            from .settings import register_menu_items
            register_menu_items(wb)
        except Exception as e:
            logger.error(f"Settings error: {e}")
    
    # 监听编辑器切换
    def on_editor_change(event=None):
        try:
            editor = wb.get_editor_notebook().get_current_editor()
            if editor:
                setup_widget(editor.get_text_widget())
        except AttributeError:
            pass  # 编辑器可能尚未初始化
        except Exception as e:
            logger.debug(f"Editor change error: {e}")
    
    wb.bind("<<NotebookTabChanged>>", on_editor_change, add=True)
    wb.after(1000, on_editor_change)
    
    logger.info(f"📦 AI Client: {HAS_AI_CLIENT}")
    logger.info("📂 Open Folder: Ctrl+Shift+O")
    logger.info("✅ Loaded!")


if __name__ == "__main__":
    print("AI Completion Plugin")
