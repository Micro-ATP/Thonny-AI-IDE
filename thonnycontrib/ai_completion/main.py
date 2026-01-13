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
AUTO_TRIGGER_DELAY_MS = 300  # 减少延迟，提高响应速度
MIN_PREFIX_LENGTH = 2  # 降低最小前缀长度，更快触发

# 请求状态常量
REQUEST_STATE_IDLE = 0
REQUEST_STATE_REQUESTING = 1
REQUEST_STATE_SHOWING = 2

# 补全模式
COMPLETION_MODE_INSERT = "completion"  # 普通补全（在光标处插入）
COMPLETION_MODE_FIX = "fix"  # 修复模式（替换选中代码）


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
        
        # 替换模式相关属性
        self._replacement_mode = False
        self._original_text = ""
        self._replacement_start = None
        self._replacement_end = None
        self._original_cursor = None
        
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
            self._reset_global_state()
            return "break"
        return None
    
    def _on_interrupt(self, event):
        """鼠标点击等中断操作"""
        if self.active:
            # 使用 after_idle 确保在事件处理完成后清除
            self.widget.after_idle(self._clear_and_reset)
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
            self.widget.after_idle(self._clear_and_reset)
        return None
    
    def _clear_and_reset(self):
        """清除并重置全局状态"""
        self._clear()
        self._reset_global_state()
    
    def _reset_global_state(self):
        """重置全局请求状态"""
        global _request_state
        with _request_lock:
            _request_state = REQUEST_STATE_IDLE
    
    def show(self, text: str, suffix: str = "") -> bool:
        """
        显示补全建议
        
        Args:
            text: 建议文本
            suffix: 光标后的代码（用于检测重叠）
        """
        # 先清除旧的
        self._clear()
        
        if not text or not text.strip():
            return False
        
        try:
            # 检测并移除与后续代码的重叠部分
            if suffix:
                text = self._remove_overlap(text, suffix)
                if not text or not text.strip():
                    logger.info("Suggestion completely overlaps with existing code, skipping")
                    return False
            
            # 获取当前光标位置
            cursor_pos = self.widget.index("insert")
            
            # 保存原始光标位置（用于正确恢复）
            self._original_cursor = cursor_pos
            
            # 设置起始 mark
            self.widget.mark_set("ghost_start", cursor_pos)
            
            # 插入带标签的文本
            self.widget.insert(cursor_pos, text, ("ghost",))
            
            # 使用实际插入后的位置来设置结束 mark（更可靠）
            # 注意：insert 后光标会自动移动到插入文本的末尾
            self.widget.mark_set("ghost_end", "insert")
            
            # 把光标移回原位（用户看到的是光标在建议文本之前）
            self.widget.mark_set("insert", cursor_pos)
            
            self.ghost_text = text
            self.active = True
            
            logger.info(f"Ghost text shown: {len(text)} chars at {cursor_pos}")
            return True
            
        except Exception as e:
            logger.error(f"Show error: {e}")
            self._clear()
            return False
    
    def _remove_overlap(self, suggestion: str, suffix: str) -> str:
        """
        检测并移除建议与后续代码的重叠部分
        
        Args:
            suggestion: AI 生成的建议
            suffix: 光标后的现有代码
            
        Returns:
            移除重叠后的建议
        """
        if not suggestion or not suffix:
            return suggestion
        
        # 清理 suffix（取前 500 个字符用于比较）
        suffix_clean = suffix[:500].lstrip()
        if not suffix_clean:
            return suggestion
        
        # 策略1：检查建议末尾是否与 suffix 开头重叠
        # 例如：建议="def foo():\n    pass\n"，suffix="pass\nprint()"
        for overlap_len in range(min(len(suggestion), len(suffix_clean)), 0, -1):
            if suggestion.endswith(suffix_clean[:overlap_len]):
                trimmed = suggestion[:-overlap_len]
                if trimmed.strip():
                    logger.debug(f"Removed {overlap_len} chars overlap from end")
                    return trimmed
                break
        
        # 策略2：检查建议是否包含 suffix 的开头部分（逐行检查）
        suggestion_lines = suggestion.split('\n')
        suffix_lines = suffix_clean.split('\n')
        
        if suffix_lines and suffix_lines[0].strip():
            first_suffix_line = suffix_lines[0].strip()
            # 检查建议的最后几行是否与 suffix 重复
            for i in range(len(suggestion_lines) - 1, -1, -1):
                if suggestion_lines[i].strip() == first_suffix_line:
                    # 找到重叠，截断建议
                    trimmed_lines = suggestion_lines[:i]
                    if trimmed_lines:
                        result = '\n'.join(trimmed_lines)
                        if result.strip():
                            logger.debug(f"Removed overlapping lines from suggestion")
                            return result + '\n' if suggestion_lines[i-1].strip() else result
                    break
        
        return suggestion
    
    def show_replacement(self, text: str, selection_start: str, selection_end: str, 
                         original_text: str = "") -> bool:
        """
        显示替换建议（用于修复模式）
        
        Args:
            text: 建议的替换文本
            selection_start: 选中区域的起始位置
            selection_end: 选中区域的结束位置
            original_text: 原始选中的文本（用于取消时恢复）
        """
        # 先清除旧的
        self._clear()
        
        if not text or not text.strip():
            return False
        
        try:
            # 保存原始信息用于取消时恢复
            self._replacement_mode = True
            self._original_text = original_text
            self._replacement_start = selection_start
            self._replacement_end = selection_end
            
            # 删除选中的文本
            self.widget.delete(selection_start, selection_end)
            
            # 设置起始 mark
            self.widget.mark_set("ghost_start", selection_start)
            
            # 插入替换文本（带 ghost 标签）
            self.widget.insert(selection_start, text, ("ghost",))
            
            # 设置结束 mark
            self.widget.mark_set("ghost_end", "insert")
            
            # 光标移回起始位置
            self.widget.mark_set("insert", selection_start)
            
            self.ghost_text = text
            self.active = True
            
            logger.info(f"Replacement shown: {len(text)} chars replacing {len(original_text)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Show replacement error: {e}")
            # 尝试恢复原始文本
            try:
                if original_text:
                    self.widget.insert(selection_start, original_text)
            except:
                pass
            self._clear()
            return False
    
    def _accept(self):
        """接受补全：保留文本，移除标签，光标移到末尾，并可选地触发连续补全"""
        if not self.active:
            return
        
        try:
            start = self.widget.index("ghost_start")
            end = self.widget.index("ghost_end")
            
            # 移除 tag（保留文本）
            self.widget.tag_remove("ghost", start, end)
            
            # 光标移到补全文本末尾
            self.widget.mark_set("insert", end)
            
            # 根据模式显示不同的消息
            is_replacement = getattr(self, '_replacement_mode', False)
            if is_replacement:
                logger.info("Replacement accepted")
                get_workbench().set_status_message("✅ Fix Applied")
            else:
                logger.info("Ghost text accepted")
                get_workbench().set_status_message("✅ Completion Accepted - Tab for more")
            
            self.widget.after(2000, lambda: get_workbench().set_status_message(""))
            
            # 保存 widget 引用，因为后面要重置状态
            widget_ref = self.widget
            
        except Exception as e:
            logger.error(f"Accept error: {e}")
            widget_ref = None
            is_replacement = True  # 出错时不触发连续补全
        
        # 重置所有状态
        self.active = False
        self.ghost_text = ""
        self._replacement_mode = False
        self._original_text = ""
        self._reset_global_state()
        
        # 连续补全：非替换模式下，短暂延迟后自动触发下一次补全
        if widget_ref and not is_replacement:
            # 检查是否启用连续补全（默认启用）
            continuous_enabled = True
            try:
                if HAS_CONFIG:
                    config = AIConfig()
                    # 尝试从 completion 配置组获取
                    completion_settings = config.get("completion", {})
                    if isinstance(completion_settings, dict):
                        continuous_enabled = completion_settings.get("continuous_completion", True)
                    else:
                        continuous_enabled = config.get("continuous_completion", True)
            except:
                pass
            
            if continuous_enabled:
                def trigger_next_completion():
                    try:
                        # 检查光标是否仍在代码中（用户可能已经移动了光标）
                        cursor_pos = widget_ref.index("insert")
                        line, col = map(int, cursor_pos.split('.'))
                        
                        # 获取当前行内容
                        current_line = widget_ref.get(f"{line}.0", f"{line}.end")
                        
                        # 如果光标在行尾，自动触发下一次补全
                        if col >= len(current_line.rstrip()):
                            logger.debug("Triggering continuous completion")
                            do_completion(widget_ref, manual=False, continuous=True)
                    except Exception as e:
                        logger.debug(f"Continuous completion skipped: {e}")
                
                # 延迟 300ms 后触发，给用户反应时间
                widget_ref.after(300, trigger_next_completion)
    
    def _clear(self):
        """清除补全：删除 ghost 文本，如果是替换模式则恢复原始文本"""
        if not self.active and not self.ghost_text:
            return
        
        try:
            start = self.widget.index("ghost_start")
            end = self.widget.index("ghost_end")
            
            # 比较位置，确保 start < end
            if self.widget.compare(start, "<", end):
                # 物理删除 ghost 文本
                self.widget.delete(start, end)
                
                # 如果是替换模式，恢复原始文本
                if getattr(self, '_replacement_mode', False) and getattr(self, '_original_text', ''):
                    self.widget.insert(start, self._original_text)
                    logger.info(f"Restored original text: {len(self._original_text)} chars")
                else:
                    logger.info("Ghost text cleared")
            
        except Exception as e:
            logger.error(f"Clear error: {e}")
        
        # 重置状态
        self.active = False
        self.ghost_text = ""
        self._replacement_mode = False
        self._original_text = ""


# ==================== 全局管理 ====================
_ghost_texts = {}
_request_state = REQUEST_STATE_IDLE  # 使用状态机管理
_request_lock = threading.Lock()
_auto_timer = None
_setup_done = set()
_last_request_id = 0  # 请求ID，用于取消过期请求
_current_suffix = ""  # 保存当前请求时的 suffix，用于重叠检测


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


def _remove_boundary_overlap(suggestion: str, boundary_before: str, boundary_after: str) -> str:
    """
    移除 AI 返回结果中与边界上下文重叠的部分
    
    例如：
    - boundary_before="re", suggestion="return", 应该返回 "turn"
    - boundary_after=")", suggestion="x + y)", 应该返回 "x + y"
    
    Args:
        suggestion: AI 返回的建议
        boundary_before: 选中区域前的边界上下文
        boundary_after: 选中区域后的边界上下文
        
    Returns:
        移除重叠后的建议
    """
    if not suggestion:
        return suggestion
    
    original = suggestion
    
    # 1. 检测并移除与 boundary_before 的重叠（建议开头）
    if boundary_before:
        # 检查建议是否以 boundary_before 的内容开头
        # 例如：boundary_before="re", suggestion="return" -> "return" 以 "re" 开头? 不是
        # 但如果 boundary_before="re", suggestion="return" 合起来应该是 "rereturn"
        # 所以我们需要检查 boundary_before + suggestion 是否有重复
        
        # 策略：检查 boundary_before 的后缀是否与 suggestion 的前缀匹配
        for i in range(min(len(boundary_before), len(suggestion)), 0, -1):
            # 检查 boundary_before 的最后 i 个字符是否等于 suggestion 的前 i 个字符
            if boundary_before[-i:] == suggestion[:i]:
                # 找到重叠，但这可能是合理的（比如 "re" + "turn" = "return"）
                # 检查合并后是否形成一个完整的词
                combined = boundary_before + suggestion
                # 如果合并后有重复，则移除
                if boundary_before[-i:] == suggestion[:i]:
                    # 检查是否真的需要移除（只有当会产生重复时才移除）
                    pass
        
        # 更简单的策略：如果 suggestion 以 boundary_before 开头，移除它
        if suggestion.startswith(boundary_before) and len(boundary_before) > 0:
            suggestion = suggestion[len(boundary_before):]
            logger.debug(f"Removed boundary_before overlap: '{boundary_before}'")
    
    # 2. 检测并移除与 boundary_after 的重叠（建议结尾）
    if boundary_after and suggestion:
        # 如果 suggestion 以 boundary_after 结尾，移除它
        if suggestion.endswith(boundary_after) and len(boundary_after) > 0:
            suggestion = suggestion[:-len(boundary_after)]
            logger.debug(f"Removed boundary_after overlap: '{boundary_after}'")
        
        # 检查 suggestion 的后缀是否与 boundary_after 的前缀匹配
        for i in range(min(len(suggestion), len(boundary_after)), 0, -1):
            if suggestion[-i:] == boundary_after[:i]:
                # 找到重叠，移除
                suggestion = suggestion[:-i]
                logger.debug(f"Removed {i} chars overlap with boundary_after")
                break
    
    # 3. 清理结果
    suggestion = suggestion.strip()
    
    # 如果处理后为空，返回原始值
    if not suggestion and original.strip():
        logger.warning("Suggestion became empty after boundary removal, keeping original")
        return original.strip()
    
    return suggestion


def _expand_selection_to_boundary(widget, start_pos: str, end_pos: str):
    """
    扩展选中区域到合理的边界
    
    对于单行选中：扩展到单词边界
    对于多行选中：扩展到完整的行（保留完整的代码块）
    
    Args:
        widget: Text widget
        start_pos: 选中区域的起始位置
        end_pos: 选中区域的结束位置
        
    Returns:
        (new_start, new_end, selected_text, boundary_before, boundary_after)
    """
    try:
        start_line = int(start_pos.split('.')[0])
        end_line = int(end_pos.split('.')[0])
        start_col = int(start_pos.split('.')[1])
        end_col = int(end_pos.split('.')[1])
        
        # 判断是单行还是多行选中
        is_multiline = (end_line > start_line)
        
        if is_multiline:
            # 多行选中：扩展到完整的行
            # 起始位置扩展到行首
            new_start = f"{start_line}.0"
            
            # 结束位置扩展到行尾
            end_line_content = widget.get(f"{end_line}.0", f"{end_line}.end")
            new_end = f"{end_line}.{len(end_line_content)}"
            
            # 获取扩展后的选中文本
            selected_text = widget.get(new_start, new_end)
            
            # 多行模式下，边界上下文使用前一行和后一行
            boundary_before = ""
            boundary_after = ""
            
            if start_line > 1:
                prev_line = widget.get(f"{start_line - 1}.0", f"{start_line - 1}.end")
                boundary_before = prev_line[-50:] if len(prev_line) > 50 else prev_line
            
            next_line_num = end_line + 1
            try:
                next_line = widget.get(f"{next_line_num}.0", f"{next_line_num}.end")
                boundary_after = next_line[:50] if len(next_line) > 50 else next_line
            except:
                pass
            
            logger.debug(f"Multiline selection expanded to full lines: {start_line}-{end_line}")
        else:
            # 单行选中：扩展到单词边界
            start_line_content = widget.get(f"{start_line}.0", f"{start_line}.end")
            
            # 扩展起始位置到单词边界（向左扩展）
            new_start_col = start_col
            while new_start_col > 0:
                char = start_line_content[new_start_col - 1]
                if char.isalnum() or char == '_':
                    new_start_col -= 1
                else:
                    break
            
            # 扩展结束位置到单词边界（向右扩展）
            new_end_col = end_col
            while new_end_col < len(start_line_content):
                char = start_line_content[new_end_col]
                if char.isalnum() or char == '_':
                    new_end_col += 1
                else:
                    break
            
            new_start = f"{start_line}.{new_start_col}"
            new_end = f"{start_line}.{new_end_col}"
            
            selected_text = widget.get(new_start, new_end)
            
            # 边界上下文
            boundary_before_start = max(0, new_start_col - 20)
            boundary_before = start_line_content[boundary_before_start:new_start_col]
            
            boundary_after_end = min(len(start_line_content), new_end_col + 20)
            boundary_after = start_line_content[new_end_col:boundary_after_end]
            
            logger.debug(f"Single-line selection expanded: {start_pos}->{new_start}, {end_pos}->{new_end}")
        
        logger.debug(f"Boundary context: '{boundary_before[:20]}...' | [selection] | '...{boundary_after[-20:]}'")
        
        return new_start, new_end, selected_text, boundary_before, boundary_after
        
    except Exception as e:
        logger.error(f"Error expanding selection: {e}")
        selected_text = widget.get(start_pos, end_pos)
        return start_pos, end_pos, selected_text, "", ""


def _should_trigger(widget) -> bool:
    """判断是否应该触发补全 - 更灵敏的触发条件"""
    try:
        line = widget.get("insert linestart", "insert")
        stripped = line.strip()
        
        # 空行不触发
        if not stripped:
            return False
        
        # 关键字触发（高优先级）
        triggers = ['def ', 'class ', 'for ', 'while ', 'if ', 'elif ', 'with ', 
                   'import ', 'from ', 'return ', 'print(', 'self.', 'try:', 
                   'except', 'finally:', 'else:', 'async ', 'await ', 'lambda ',
                   'yield ', 'raise ', 'assert ', 'global ', 'nonlocal ']
        if any(stripped.startswith(t) for t in triggers):
            return True
        
        # 特殊字符结尾触发（更多触发点）
        trigger_endings = ('=', '(', '[', '{', ',', ':', '.', '+', '-', '*', '/', 
                          '>', '<', '&', '|', '%', '@', '!', '~')
        if line.rstrip().endswith(trigger_endings):
            return True
        
        # 赋值语句触发
        if '=' in stripped and not stripped.startswith('#'):
            return True
        
        # 函数调用中触发
        if '(' in stripped and not stripped.endswith(')'):
            return True
        
        # 一定长度后触发
        if len(stripped) >= MIN_PREFIX_LENGTH:
            # 任何非空格字符结尾都触发
            if stripped and stripped[-1].isalnum():
                return True
            # 空格结尾也触发
            if line.endswith(' '):
                return True
        
        return False
    except:
        return False


def do_completion(widget, manual=False, continuous=False):
    """
    执行补全请求
    
    Args:
        widget: Text widget
        manual: 是否手动触发
        continuous: 是否为连续补全（接受上一个补全后自动触发）
    """
    global _request_state, _last_request_id, _current_suffix
    
    with _request_lock:
        # 如果正在请求中，忽略新请求（防止快捷键多次按压）
        if _request_state == REQUEST_STATE_REQUESTING:
            logger.debug("Request in progress, ignoring new request")
            return
        
        # 如果已有建议显示且是手动触发，先清除再刷新
        if _request_state == REQUEST_STATE_SHOWING:
            ghost = get_ghost(widget)
            if ghost.active:
                ghost._clear()
        
        _request_state = REQUEST_STATE_REQUESTING
        _last_request_id += 1
        current_request_id = _last_request_id
    
    try:
        get_workbench().set_status_message("🤖 AI is thinking...")
    except:
        pass
    
    try:
        # 检测是否有选中的代码（用于修复模式）
        selected_text = ""
        selection_start = None
        selection_end = None
        completion_mode = COMPLETION_MODE_INSERT
        boundary_before = ""  # 选中区域前的边界上下文
        boundary_after = ""   # 选中区域后的边界上下文
        
        try:
            # 尝试获取选中的文本
            raw_selection = widget.get("sel.first", "sel.last")
            if raw_selection and raw_selection.strip():
                raw_start = widget.index("sel.first")
                raw_end = widget.index("sel.last")
                
                # 扩展选中区域到合理的边界
                selection_start, selection_end, selected_text, boundary_before, boundary_after = \
                    _expand_selection_to_boundary(widget, raw_start, raw_end)
                
                completion_mode = COMPLETION_MODE_FIX
                logger.info(f"Selection expanded: '{raw_selection[:20]}...' -> '{selected_text[:20]}...' "
                           f"(boundary: '{boundary_before}' | '{boundary_after}')")
        except tk.TclError:
            # 没有选中文本，使用普通补全模式
            pass
        
        # 获取上下文
        if HAS_COMPLETION_HANDLER:
            ctx = get_smart_context(widget)
            prefix = ctx.get("prefix", "")
            suffix = ctx.get("suffix", "")
        else:
            prefix = widget.get("1.0", "insert")
            suffix = widget.get("insert", "end-1c")
        
        # 如果是修复模式，调整 prefix 和 suffix
        if completion_mode == COMPLETION_MODE_FIX and selection_start:
            prefix = widget.get("1.0", selection_start)
            suffix = widget.get(selection_end, "end-1c")
        
        # 保存 suffix 用于后续重叠检测
        _current_suffix = suffix
        
        # 检查长度（修复模式跳过此检查）
        if completion_mode == COMPLETION_MODE_INSERT:
            if not manual and len(prefix.strip()) < MIN_PREFIX_LENGTH:
                with _request_lock:
                    _request_state = REQUEST_STATE_IDLE
                get_workbench().set_status_message("")
                return
        
        # 构建请求
        client = AIClient()
        context = {
            "text": prefix + (selected_text if selected_text else "") + suffix,
            "prefix": prefix,
            "suffix": suffix,
            "selection": selected_text,
            "boundary_before": boundary_before,  # 选中区域前的边界上下文
            "boundary_after": boundary_after,    # 选中区域后的边界上下文
            "language": "python",
            "mode": completion_mode
        }
        
        def request_thread():
            global _request_state
            try:
                result = client.request(context)
                # 检查请求是否已过期
                with _request_lock:
                    if current_request_id != _last_request_id:
                        logger.debug(f"Request {current_request_id} expired, ignoring result")
                        return
                # 传递更多信息用于结果处理
                widget.after(0, lambda: _handle_result(
                    result, widget, suffix, 
                    completion_mode, selection_start, selection_end, selected_text,
                    boundary_before, boundary_after
                ))
            except Exception as e:
                logger.error(f"Request error: {e}")
                widget.after(0, lambda: _handle_error(str(e), widget))
            finally:
                with _request_lock:
                    if current_request_id == _last_request_id:
                        if _request_state == REQUEST_STATE_REQUESTING:
                            _request_state = REQUEST_STATE_IDLE
        
        threading.Thread(target=request_thread, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Completion error: {e}")
        with _request_lock:
            _request_state = REQUEST_STATE_IDLE
        _handle_error(str(e), widget)


def _handle_result(result: dict, widget, suffix: str = "", 
                   completion_mode: str = COMPLETION_MODE_INSERT,
                   selection_start: str = None, selection_end: str = None,
                   original_selection: str = "",
                   boundary_before: str = "", boundary_after: str = ""):
    """处理 AI 返回结果"""
    global _request_state
    
    try:
        get_workbench().set_status_message("")
    except:
        pass
    
    if not result.get("success"):
        # Bug 4 修复：显示明确的错误信息
        error_msg = result.get("message", "Unknown error")
        _handle_error(error_msg, widget)
        return
    
    suggestion = result.get("data", {}).get("raw_analysis", "")
    if suggestion and suggestion.strip():
        # 如果是修复模式，检测并移除与边界上下文的重叠
        if completion_mode == COMPLETION_MODE_FIX:
            suggestion = _remove_boundary_overlap(suggestion, boundary_before, boundary_after)
            logger.debug(f"After boundary overlap removal: '{suggestion[:50]}...'")
        
        ghost = get_ghost(widget)
        
        if completion_mode == COMPLETION_MODE_FIX and selection_start and selection_end:
            # 修复模式：替换选中的代码
            if ghost.show_replacement(suggestion, selection_start, selection_end, original_selection):
                with _request_lock:
                    _request_state = REQUEST_STATE_SHOWING
                get_workbench().set_status_message("🔧 Fix suggested - Tab to accept, Esc to cancel")
            else:
                with _request_lock:
                    _request_state = REQUEST_STATE_IDLE
        else:
            # 普通补全模式：在光标处插入
            if ghost.show(suggestion, suffix):
                with _request_lock:
                    _request_state = REQUEST_STATE_SHOWING
            else:
                with _request_lock:
                    _request_state = REQUEST_STATE_IDLE
    else:
        with _request_lock:
            _request_state = REQUEST_STATE_IDLE
        get_workbench().set_status_message("💭 No suggestion available")
        widget.after(2000, lambda: get_workbench().set_status_message(""))


def _handle_error(error_msg: str, widget):
    """处理错误，显示用户友好的提示"""
    global _request_state
    
    with _request_lock:
        _request_state = REQUEST_STATE_IDLE
    
    try:
        get_workbench().set_status_message("")
    except:
        pass
    
    # 分析错误类型，给出具体提示
    error_display = error_msg
    show_settings_hint = False
    
    if "API" in error_msg and ("密钥" in error_msg or "key" in error_msg.lower() or "401" in error_msg):
        error_display = "❌ API key is invalid or not configured"
        show_settings_hint = True
    elif "endpoint" in error_msg.lower() or "连接" in error_msg or "connect" in error_msg.lower():
        error_display = "❌ Failed to connect to the API endpoint"
        show_settings_hint = True
    elif "timeout" in error_msg.lower() or "超时" in error_msg:
        error_display = "❌ Request timed out, please try again later"
    elif "429" in error_msg:
        error_display = "❌ Requests are too frequent, please try again later."
    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
        error_display = "Network connection failed"
    elif "refused" in error_msg.lower():
        error_display = "Connection refused by server"
    elif "404" in error_msg:
        error_display = "API endpoint not found (404)"
        show_settings_hint = True
    elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
        error_display = "Server error, please try again later"
    elif "配置" in error_msg or "config" in error_msg.lower():
        error_display = "❌ API configuration error"
        show_settings_hint = True
    else:
        error_display = f"❌ {error_msg[:50]}" if len(error_msg) > 50 else f"❌ {error_msg}"
    
    # 在状态栏显示错误
    try:
        wb = get_workbench()
        wb.set_status_message(error_display)
        
        # 如果需要引导用户去设置页面
        def show_error_dialog():
            from tkinter import messagebox

            if show_settings_hint:
                result = messagebox.askyesno(
                    "AI API Connection Failed",
                    f"Error: {error_display}\n\n"
                    "The AI code completion service could not be reached.\n\n"
                    "Please check if the API configuration is correct.\n\n"
                    "Would you like to open the settings page?",
                    icon="error"
                )
                if result:
                    try:
                        if HAS_SETTINGS:
                            from .settings import open_settings_dialog
                            open_settings_dialog()
                    except Exception as e:
                        logger.error(f"Failed to open settings: {e}")
            else:
                messagebox.showerror(
                    "AI API Connection Failed",
                    f"Error: {error_display}\n\n"
                    "The AI code completion service could not be reached.\n\n"
                    "Please check your network connection and try again."
                )

        widget.after(100, show_error_dialog)
        widget.after(3000, lambda: wb.set_status_message(""))
            
    except Exception as e:
        logger.error(f"Error showing error message: {e}")


def trigger_ai_completion(event=None):
    """手动触发补全"""
    global _request_state
    
    try:
        editor = get_workbench().get_editor_notebook().get_current_editor()
        if not editor:
            return "break"
        
        widget = editor.get_text_widget()
        setup_widget(widget)
        
        ghost = get_ghost(widget)
        
        # Bug 2 修复：检查当前状态
        with _request_lock:
            current_state = _request_state
        
        if current_state == REQUEST_STATE_REQUESTING:
            # 正在请求中，忽略重复按键
            logger.debug("Request in progress, ignoring trigger")
            return "break"
        
        if current_state == REQUEST_STATE_SHOWING and ghost.active:
            # 已有建议显示，再次按键刷新建议
            logger.info("Refreshing suggestion...")
            ghost._clear()
            with _request_lock:
                _request_state = REQUEST_STATE_IDLE
        
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
        showerror("Error", f"Can not open AI dialog box:\n\n{e}")
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
            chat_display.insert(tk.END, f"\n❌ Error: {text}\n")
        chat_display.config(state=tk.DISABLED)
        chat_display.see(tk.END)

    def send_message():
        message = input_text.get("1.0", tk.END).strip()
        if not message:
            return

        input_text.delete("1.0", tk.END)
        append_message("user", message)
        status_var.set("🤔 AI is thinking...")

        def request_thread():
            try:
                if not HAS_AI_CLIENT:
                    dialog.after(0, lambda: append_message("error", "AI Client not loaded"))
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
                        append_message("ai", response if response else "(No response)")
                        status_var.set("✅ Finish")
                    else:
                        append_message("error", result.get("message", "Unknown error"))
                        status_var.set("❌ Failed")

                dialog.after(0, handle_result)
            except Exception as e:
                dialog.after(0, lambda: append_message("error", str(e)))
                dialog.after(0, lambda: status_var.set("❌ Error"))

        threading.Thread(target=request_thread, daemon=True).start()

    send_btn = tk.Button(input_frame, text="send", command=send_message, width=8)
    send_btn.pack(side=tk.RIGHT)

    def on_enter(event):
        if not (event.state & 0x1):
            send_message()
            return "break"

    input_text.bind("<Return>", on_enter)
    append_message("ai", "Anything I can do to help you？")


# ==========  添加结束 ==========


def analyze_and_fix_code(event=None):
    """
    分析并修复代码 - 支持多行代码修复
    
    如果有选中代码：分析并修复选中的代码
    如果没有选中：分析并修复整个文件
    """
    try:
        editor = get_workbench().get_editor_notebook().get_current_editor()
        if not editor:
            from tkinter import messagebox
            messagebox.showwarning("Prompt", "Please open a file first.")
            return "break"
        
        widget = editor.get_text_widget()
        
        # 检测是否有选中的代码
        selected_text = ""
        try:
            selected_text = widget.get("sel.first", "sel.last")
        except tk.TclError:
            pass
        
        if selected_text and selected_text.strip():
            # 有选中代码，显示修复对话框
            _show_fix_dialog(widget, selected_text)
        else:
            # 没有选中代码，分析整个文件
            full_code = widget.get("1.0", "end-1c")
            if not full_code.strip():
                from tkinter import messagebox
                messagebox.showinfo("Prompt", "The file is empty, no analysis is needed")
                return "break"
            _show_fix_dialog(widget, full_code, is_full_file=True)
        
    except Exception as e:
        logger.error(f"Analyze and fix error: {e}")
        from tkinter import messagebox
        messagebox.showerror("Error", f"Analysis failed: {e}")
    
    return "break"


def _show_fix_dialog(widget, code_to_fix: str, is_full_file: bool = False):
    """显示代码修复对话框"""
    from tkinter import scrolledtext
    
    wb = get_workbench()
    
    dialog = tk.Toplevel(wb)
    dialog.title("🔧 AI Code Analysis & Fix")
    dialog.geometry("800x600")
    dialog.transient(wb)
    
    main_frame = tk.Frame(dialog, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 标题
    title_text = "🔧 Analyze the entire code file" if is_full_file else "🔧 Analyze the selected part of code"
    title = tk.Label(main_frame, text=title_text, font=("Arial", 14, "bold"))
    title.pack(pady=(0, 10))
    
    # 原始代码显示
    orig_frame = tk.LabelFrame(main_frame, text="Original code")
    orig_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    orig_text = scrolledtext.ScrolledText(orig_frame, wrap=tk.WORD, height=8,
                                          bg="#2d2d2d", fg="#ffffff", font=("Consolas", 10))
    orig_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    orig_text.insert("1.0", code_to_fix)
    orig_text.config(state=tk.DISABLED)
    
    # 修复后代码显示
    fix_frame = tk.LabelFrame(main_frame, text="AI modify Suggestions")
    fix_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
    
    fix_text = scrolledtext.ScrolledText(fix_frame, wrap=tk.WORD, height=8,
                                         bg="#1a3a1a", fg="#ffffff", font=("Consolas", 10))
    fix_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 状态栏
    status_var = tk.StringVar(value="Press「Analyze Code」to start")
    status_label = tk.Label(main_frame, textvariable=status_var, fg="gray")
    status_label.pack(pady=(5, 0))
    
    # 按钮区域
    btn_frame = tk.Frame(main_frame)
    btn_frame.pack(pady=(10, 0))
    
    def do_analyze():
        """执行分析"""
        status_var.set("🤖 AI is thinking...")
        analyze_btn.config(state=tk.DISABLED)
        fix_text.config(state=tk.NORMAL)
        fix_text.delete("1.0", tk.END)
        fix_text.insert("1.0", "AI is thinking, please wait...")
        fix_text.config(state=tk.DISABLED)
        
        def request_thread():
            try:
                client = AIClient()
                
                # 构建分析请求
                context = {
                    "text": code_to_fix,
                    "prefix": "",
                    "suffix": "",
                    "selection": code_to_fix,
                    "language": "python",
                    "mode": "analyze_fix"
                }
                
                result = client.request(context)

                def handle_result():
                    analyze_btn.config(state=tk.NORMAL)
                    if result.get("success"):
                        fixed_code = result.get("data", {}).get("raw_analysis", "")
                        fix_text.config(state=tk.NORMAL)
                        fix_text.delete("1.0", tk.END)
                        if fixed_code:
                            fix_text.insert("1.0", fixed_code)
                            status_var.set("✅ Analysis completed - Click 'Apply Fix' to replace code")
                            apply_btn.config(state=tk.NORMAL)
                        else:
                            fix_text.insert("1.0", "No issues detected that require fixing")
                            status_var.set("✅ Code appears to be error-free")
                        fix_text.config(state=tk.DISABLED)
                    else:
                        error_msg = result.get("message", "Unknown error")
                        fix_text.config(state=tk.NORMAL)
                        fix_text.delete("1.0", tk.END)
                        fix_text.insert("1.0", f"Analysis failed: {error_msg}")
                        fix_text.config(state=tk.DISABLED)
                        status_var.set(f"❌ {error_msg[:30]}...")

                dialog.after(0, handle_result)

            except Exception as e:
                def show_error():
                    analyze_btn.config(state=tk.NORMAL)
                    fix_text.config(state=tk.NORMAL)
                    fix_text.delete("1.0", tk.END)
                    fix_text.insert("1.0", f"Error: {e}")
                    fix_text.config(state=tk.DISABLED)
                    status_var.set("❌ Analyze failed")
                dialog.after(0, show_error)

        threading.Thread(target=request_thread, daemon=True).start()

    def do_apply():
        """应用修复"""
        fix_text.config(state=tk.NORMAL)
        fixed_code = fix_text.get("1.0", "end-1c")
        fix_text.config(state=tk.DISABLED)

        if not fixed_code or fixed_code.startswith("Analyzing") or fixed_code.startswith("分析失败"):
            from tkinter import messagebox
            messagebox.showwarning("Prompt", "No fixable code available")
            return

        if is_full_file:
            # 替换整个文件
            widget.delete("1.0", "end")
            widget.insert("1.0", fixed_code)
        else:
            # 替换选中的代码
            try:
                sel_start = widget.index("sel.first")
                sel_end = widget.index("sel.last")
                widget.delete(sel_start, sel_end)
                widget.insert(sel_start, fixed_code)
            except tk.TclError:
                # 选中可能已经丢失，插入到光标位置
                widget.insert("insert", fixed_code)

        status_var.set("✅ Fix applied successfully")
        dialog.after(1500, dialog.destroy)

    analyze_btn = tk.Button(btn_frame, text="🔍 Analyze Code", command=do_analyze, width=15)
    analyze_btn.pack(side=tk.LEFT, padx=5)

    apply_btn = tk.Button(btn_frame, text="✅ Apply Fix", command=do_apply, width=15, state=tk.DISABLED)
    apply_btn.pack(side=tk.LEFT, padx=5)

    close_btn = tk.Button(btn_frame, text="Close", command=dialog.destroy, width=10)
    close_btn.pack(side=tk.LEFT, padx=5)

    # 绑定快捷键
    dialog.bind('<Escape>', lambda e: dialog.destroy())

    # 居中显示
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")

    dialog.grab_set()


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
    
    # 注册分析修复代码命令
    wb.add_command(
        command_id="ai_completion.analyze_fix",
        menu_name="tools",
        command_label="Analyze & Fix Code...",
        handler=analyze_and_fix_code,
        default_sequence="<Control-Alt-f>",
        accelerator="Ctrl+Alt+F",
        group=102
    )
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
