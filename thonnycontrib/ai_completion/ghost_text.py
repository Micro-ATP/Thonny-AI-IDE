# ghost_text.py
"""
Ghost Text Module - GitHub Copilot Style Inline Suggestions
实现类似 GitHub Copilot 的幽灵文本（Ghost Text）补全效果

特点：
- 灰色半透明文字显示建议
- Tab 接受整个建议
- Esc 或继续输入取消建议
- 支持多行建议
- 智能缩进处理
"""
import tkinter as tk
from tkinter import font as tkfont
from logging import getLogger
from typing import Optional, Tuple
import re

logger = getLogger(__name__)

# ==================== 配置 ====================
GHOST_TEXT_TAG = "ai_ghost_text"
GHOST_TEXT_FG = "#888888"  # 灰色文字
GHOST_TEXT_FONT_STYLE = "italic"  # 斜体


class GhostTextManager:
    """
    Ghost Text 管理器 - 实现 Copilot 风格的内联建议
    
    用法：
        manager = GhostTextManager(text_widget)
        manager.show_suggestion("suggested code here")
        # 用户按 Tab -> manager.accept()
        # 用户按 Esc 或输入 -> manager.dismiss()
    """
    
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self.is_active = False
        self.suggestion_text = ""
        self.suggestion_start = None
        self.suggestion_end = None
        self.original_cursor_pos = None
        
        # 设置 Ghost Text 样式
        self._setup_ghost_style()
        
        # 绑定事件
        self._setup_bindings()
        
        logger.info("GhostTextManager initialized")
    
    def _setup_ghost_style(self):
        """设置幽灵文本样式"""
        try:
            # 获取当前字体
            current_font = self.text_widget.cget("font")
            
            # 创建斜体版本
            if isinstance(current_font, str):
                # 字符串格式的字体
                self.text_widget.tag_configure(
                    GHOST_TEXT_TAG,
                    foreground=GHOST_TEXT_FG,
                    font=(current_font, 10, GHOST_TEXT_FONT_STYLE)
                )
            else:
                # 已经是 font 对象
                self.text_widget.tag_configure(
                    GHOST_TEXT_TAG,
                    foreground=GHOST_TEXT_FG
                )
            
            # 设置标签优先级（低于选择，高于普通文本）
            self.text_widget.tag_lower(GHOST_TEXT_TAG, "sel")
            
        except Exception as e:
            logger.warning(f"Could not setup ghost style: {e}")
            # 后备样式
            self.text_widget.tag_configure(
                GHOST_TEXT_TAG,
                foreground=GHOST_TEXT_FG
            )
    
    def _setup_bindings(self):
        """设置键盘绑定"""
        # 使用 add=True 不覆盖现有绑定
        self.text_widget.bind("<Tab>", self._on_tab, add=True)
        self.text_widget.bind("<Escape>", self._on_escape, add=True)
        self.text_widget.bind("<Key>", self._on_key, add=True)
        self.text_widget.bind("<Button-1>", self._on_click, add=True)
    
    def show_suggestion(self, suggestion: str) -> bool:
        """
        显示 Ghost Text 建议
        
        Args:
            suggestion: 建议的代码文本
            
        Returns:
            是否成功显示
        """
        # 先清除现有建议
        self.dismiss()
        
        if not suggestion or not suggestion.strip():
            return False
        
        try:
            # 保存原始光标位置
            self.original_cursor_pos = self.text_widget.index("insert")
            
            # 获取当前行的缩进
            current_line_start = self.text_widget.index("insert linestart")
            line_before_cursor = self.text_widget.get(current_line_start, "insert")
            current_indent = self._get_indent(line_before_cursor)
            
            # 处理建议文本（调整缩进）
            processed_suggestion = self._process_suggestion(suggestion, current_indent)
            
            # 保存建议信息
            self.suggestion_text = processed_suggestion
            self.suggestion_start = self.text_widget.index("insert")
            
            # 插入幽灵文本
            self.text_widget.insert("insert", processed_suggestion, (GHOST_TEXT_TAG,))
            
            # 记录结束位置
            self.suggestion_end = self.text_widget.index("insert")
            
            # 将光标移回原位置
            self.text_widget.mark_set("insert", self.suggestion_start)
            
            # 标记为活跃
            self.is_active = True
            
            logger.debug(f"Ghost text shown: {len(processed_suggestion)} chars")
            return True
            
        except Exception as e:
            logger.error(f"Error showing ghost text: {e}")
            self.dismiss()
            return False
    
    def _process_suggestion(self, suggestion: str, current_indent: str) -> str:
        """
        处理建议文本，调整缩进
        
        Args:
            suggestion: 原始建议
            current_indent: 当前行的缩进
            
        Returns:
            处理后的建议
        """
        lines = suggestion.split('\n')
        if len(lines) <= 1:
            return suggestion
        
        # 第一行不需要额外缩进
        result_lines = [lines[0]]
        
        # 后续行需要添加当前缩进
        for line in lines[1:]:
            if line.strip():  # 非空行
                # 检测原始缩进
                original_indent = self._get_indent(line)
                # 添加当前行的基础缩进
                result_lines.append(current_indent + line.lstrip())
            else:
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _get_indent(self, line: str) -> str:
        """获取行的缩进部分"""
        match = re.match(r'^(\s*)', line)
        return match.group(1) if match else ""
    
    def accept(self) -> bool:
        """
        接受当前建议
        
        Returns:
            是否成功接受
        """
        if not self.is_active:
            return False
        
        try:
            # 移除 ghost text 标签，但保留文本
            self.text_widget.tag_remove(
                GHOST_TEXT_TAG,
                self.suggestion_start,
                self.suggestion_end
            )
            
            # 将光标移到建议末尾
            self.text_widget.mark_set("insert", self.suggestion_end)
            
            logger.info(f"Ghost text accepted: {len(self.suggestion_text)} chars")
            
            # 重置状态
            self._reset_state()
            
            return True
            
        except Exception as e:
            logger.error(f"Error accepting ghost text: {e}")
            self._reset_state()
            return False
    
    def dismiss(self) -> bool:
        """
        取消/隐藏当前建议
        
        Returns:
            是否有建议被取消
        """
        if not self.is_active:
            return False
        
        try:
            # 删除幽灵文本
            if self.suggestion_start and self.suggestion_end:
                self.text_widget.delete(self.suggestion_start, self.suggestion_end)
            
            # 移除标签
            self.text_widget.tag_remove(GHOST_TEXT_TAG, "1.0", "end")
            
            logger.debug("Ghost text dismissed")
            
        except Exception as e:
            logger.warning(f"Error dismissing ghost text: {e}")
        
        self._reset_state()
        return True
    
    def _reset_state(self):
        """重置状态"""
        self.is_active = False
        self.suggestion_text = ""
        self.suggestion_start = None
        self.suggestion_end = None
        self.original_cursor_pos = None
    
    # ==================== 事件处理 ====================
    
    def _on_tab(self, event) -> Optional[str]:
        """Tab 键处理 - 接受建议"""
        if self.is_active:
            self.accept()
            return "break"  # 阻止默认 Tab 行为
        return None  # 允许正常 Tab
    
    def _on_escape(self, event) -> Optional[str]:
        """Escape 键处理 - 取消建议"""
        if self.is_active:
            self.dismiss()
            return "break"
        return None
    
    def _on_key(self, event) -> Optional[str]:
        """
        按键处理 - 输入时取消建议
        """
        # 忽略修饰键和特殊键
        if event.keysym in ('Tab', 'Escape', 'Shift_L', 'Shift_R',
                           'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
                           'Super_L', 'Super_R', 'Caps_Lock', 'Return',
                           'Up', 'Down', 'Left', 'Right', 'Home', 'End',
                           'Prior', 'Next'):  # Page Up/Down
            return None
        
        # 如果有活跃的建议且用户输入了其他字符，取消建议
        if self.is_active and event.char and event.char.isprintable():
            self.dismiss()
        
        return None
    
    def _on_click(self, event) -> None:
        """鼠标点击处理 - 取消建议"""
        if self.is_active:
            self.dismiss()


class CopilotStyleCompleter:
    """
    Copilot 风格补全器
    整合 Ghost Text 和 AI 请求
    """
    
    def __init__(self, text_widget: tk.Text, ai_client=None):
        self.text_widget = text_widget
        self.ai_client = ai_client
        self.ghost_manager = GhostTextManager(text_widget)
        
        # 自动触发配置
        self.auto_trigger_enabled = False
        self.auto_trigger_delay_ms = 500
        self._auto_trigger_timer = None
        
        # 手动触发的快捷键已在 main.py 中绑定
        
    def set_ai_client(self, client):
        """设置 AI 客户端"""
        self.ai_client = client
    
    def enable_auto_trigger(self, enabled: bool = True, delay_ms: int = 500):
        """
        启用/禁用自动触发
        
        Args:
            enabled: 是否启用
            delay_ms: 触发延迟（毫秒）
        """
        self.auto_trigger_enabled = enabled
        self.auto_trigger_delay_ms = delay_ms
        
        if enabled:
            self.text_widget.bind("<KeyRelease>", self._on_key_release, add=True)
            logger.info(f"Auto-trigger enabled with {delay_ms}ms delay")
        else:
            self.text_widget.unbind("<KeyRelease>")
            logger.info("Auto-trigger disabled")
    
    def _on_key_release(self, event):
        """按键释放时检查是否应该触发补全"""
        if not self.auto_trigger_enabled:
            return
        
        # 取消之前的定时器
        if self._auto_trigger_timer:
            self.text_widget.after_cancel(self._auto_trigger_timer)
        
        # 检查是否应该触发
        if self._should_auto_trigger(event):
            self._auto_trigger_timer = self.text_widget.after(
                self.auto_trigger_delay_ms,
                self._do_auto_trigger
            )
    
    def _should_auto_trigger(self, event) -> bool:
        """判断是否应该自动触发"""
        # 忽略非打印字符
        if not event.char or not event.char.isprintable():
            return False
        
        # 如果已经有活跃的建议，不触发
        if self.ghost_manager.is_active:
            return False
        
        # 可以添加更多逻辑，如：
        # - 检查是否在字符串/注释中
        # - 检查输入的字符类型
        # - 最小输入长度要求
        
        return True
    
    def _do_auto_trigger(self):
        """执行自动触发"""
        if self.ai_client:
            # 这里可以调用 main.py 中的 trigger_ai_completion
            # 或者直接请求 AI
            pass
    
    def show_suggestion(self, suggestion: str) -> bool:
        """显示建议"""
        return self.ghost_manager.show_suggestion(suggestion)
    
    def accept(self) -> bool:
        """接受建议"""
        return self.ghost_manager.accept()
    
    def dismiss(self) -> bool:
        """取消建议"""
        return self.ghost_manager.dismiss()
    
    @property
    def is_active(self) -> bool:
        """是否有活跃的建议"""
        return self.ghost_manager.is_active


# ==================== 便捷函数 ====================

_completers = {}  # 缓存每个 text_widget 的 completer

def get_completer(text_widget: tk.Text) -> CopilotStyleCompleter:
    """获取或创建补全器实例"""
    widget_id = id(text_widget)
    if widget_id not in _completers:
        _completers[widget_id] = CopilotStyleCompleter(text_widget)
    return _completers[widget_id]


def show_ghost_suggestion(text_widget: tk.Text, suggestion: str) -> bool:
    """便捷函数：显示幽灵文本建议"""
    completer = get_completer(text_widget)
    return completer.show_suggestion(suggestion)


def accept_ghost_suggestion(text_widget: tk.Text) -> bool:
    """便捷函数：接受建议"""
    completer = get_completer(text_widget)
    return completer.accept()


def dismiss_ghost_suggestion(text_widget: tk.Text) -> bool:
    """便捷函数：取消建议"""
    completer = get_completer(text_widget)
    return completer.dismiss()

