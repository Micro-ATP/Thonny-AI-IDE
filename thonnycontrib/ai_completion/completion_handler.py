# completion_handler.py
"""
Completion Handler Module - Sprint 3
负责处理代码补全的核心逻辑，包括：
- 上下文窗口管理
- 内联建议显示
- 防抖机制
- 边缘情况处理
"""
import time
import threading
from logging import getLogger
from typing import Dict, Any, Optional, Tuple

logger = getLogger(__name__)

# ==================== 配置常量 ====================
# 上下文窗口配置
CONTEXT_LINES_BEFORE = 50  # 光标前的行数
CONTEXT_LINES_AFTER = 10   # 光标后的行数
MAX_CONTEXT_CHARS = 4000   # 最大上下文字符数
MAX_FILE_SIZE = 100000     # 最大文件大小（字符），超过此值会警告

# 防抖配置
DEBOUNCE_DELAY_MS = 500    # 防抖延迟（毫秒）
MIN_TRIGGER_INTERVAL_MS = 1000  # 最小触发间隔（毫秒）

# 内联建议样式
SUGGESTION_TAG = "ai_inline_suggestion"
SUGGESTION_BG_COLOR = "#E8F5E9"  # 浅绿色背景
SUGGESTION_FG_COLOR = "#666666"  # 灰色文字


class CompletionState:
    """补全状态管理"""
    
    def __init__(self):
        self.is_requesting = False  # 是否正在请求
        self.is_suggestion_active = False  # 是否有活跃的建议
        self.current_suggestion = None  # 当前建议文本
        self.suggestion_start_pos = None  # 建议插入位置
        self.suggestion_end_pos = None  # 建议结束位置
        self.last_trigger_time = 0  # 上次触发时间
        self.request_id = 0  # 请求ID（用于取消过期请求）
        
    def reset(self):
        """重置状态"""
        self.is_suggestion_active = False
        self.current_suggestion = None
        self.suggestion_start_pos = None
        self.suggestion_end_pos = None


class ContextExtractor:
    """上下文提取器 - 实现智能上下文窗口"""
    
    @staticmethod
    def extract_context(text_widget, cursor_pos: str = None) -> Dict[str, Any]:
        """
        从编辑器提取上下文
        
        Args:
            text_widget: Tkinter Text 组件
            cursor_pos: 光标位置（格式："line.column"），默认为当前位置
            
        Returns:
            包含上下文信息的字典
        """
        try:
            # 获取光标位置
            if cursor_pos is None:
                cursor_pos = text_widget.index("insert")
            
            # 解析行列号
            line, col = map(int, cursor_pos.split('.'))
            
            # 获取完整代码
            full_text = text_widget.get("1.0", "end-1c")
            lines = full_text.splitlines(keepends=True)
            total_lines = len(lines)
            
            # 计算上下文窗口范围
            start_line = max(1, line - CONTEXT_LINES_BEFORE)
            end_line = min(total_lines, line + CONTEXT_LINES_AFTER)
            
            # 提取上下文
            context_before_lines = lines[start_line - 1:line - 1]
            current_line = lines[line - 1] if line <= len(lines) else ""
            context_after_lines = lines[line:end_line] if line < len(lines) else []
            
            # 当前行光标前后的内容
            current_line_before = current_line[:col] if col <= len(current_line) else current_line
            current_line_after = current_line[col:] if col <= len(current_line) else ""
            
            # 组合上下文
            prefix = ''.join(context_before_lines) + current_line_before
            suffix = current_line_after + ''.join(context_after_lines)
            
            # 检查并限制上下文大小
            if len(prefix) > MAX_CONTEXT_CHARS // 2:
                prefix = prefix[-(MAX_CONTEXT_CHARS // 2):]
                logger.debug(f"Prefix truncated to {len(prefix)} chars")
            
            if len(suffix) > MAX_CONTEXT_CHARS // 2:
                suffix = suffix[:MAX_CONTEXT_CHARS // 2]
                logger.debug(f"Suffix truncated to {len(suffix)} chars")
            
            # 获取当前行的缩进
            indent = ContextExtractor._get_line_indent(current_line_before)
            
            return {
                "prefix": prefix,
                "suffix": suffix,
                "current_line": current_line,
                "current_line_before": current_line_before,
                "current_line_after": current_line_after,
                "cursor_line": line,
                "cursor_col": col,
                "total_lines": total_lines,
                "total_chars": len(full_text),
                "indent": indent,
                "context_start_line": start_line,
                "context_end_line": end_line,
            }
            
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return {
                "prefix": "",
                "suffix": "",
                "current_line": "",
                "cursor_line": 1,
                "cursor_col": 0,
                "total_lines": 0,
                "total_chars": 0,
                "indent": "",
                "error": str(e)
            }
    
    @staticmethod
    def _get_line_indent(line: str) -> str:
        """获取行的缩进"""
        indent = ""
        for char in line:
            if char in (' ', '\t'):
                indent += char
            else:
                break
        return indent
    
    @staticmethod
    def check_file_size(text_widget) -> Tuple[bool, int, str]:
        """
        检查文件大小
        
        Returns:
            (is_ok, size, message)
        """
        try:
            full_text = text_widget.get("1.0", "end-1c")
            size = len(full_text)
            
            if size == 0:
                return True, size, "empty_file"
            elif size > MAX_FILE_SIZE:
                return False, size, f"File too large ({size} chars > {MAX_FILE_SIZE} limit)"
            else:
                return True, size, "ok"
                
        except Exception as e:
            return False, 0, f"Error checking file size: {e}"


class InlineSuggestionManager:
    """内联建议管理器 - 实现流畅的建议显示和交互"""
    
    def __init__(self, text_widget, state: CompletionState):
        self.text_widget = text_widget
        self.state = state
        self._setup_tag()
        
    def _setup_tag(self):
        """设置建议文本的样式标签"""
        self.text_widget.tag_configure(
            SUGGESTION_TAG,
            background=SUGGESTION_BG_COLOR,
            foreground=SUGGESTION_FG_COLOR,
            font=("Courier New", 10, "italic")
        )
        # 设置标签优先级（低于选择）
        self.text_widget.tag_lower(SUGGESTION_TAG, "sel")
    
    def show_suggestion(self, suggestion: str, preserve_indent: bool = True) -> bool:
        """
        在光标位置显示内联建议
        
        Args:
            suggestion: 建议文本
            preserve_indent: 是否保持当前行的缩进
            
        Returns:
            是否成功显示
        """
        try:
            # 先清除现有建议
            self.hide_suggestion()
            
            if not suggestion or suggestion.isspace():
                logger.debug("Empty suggestion, not showing")
                return False
            
            # 获取当前光标位置
            cursor_pos = self.text_widget.index("insert")
            
            # 如果需要，调整缩进
            if preserve_indent:
                # 获取当前行的缩进
                line_start = self.text_widget.index(f"{cursor_pos} linestart")
                line_content = self.text_widget.get(line_start, cursor_pos)
                current_indent = ""
                for char in line_content:
                    if char in (' ', '\t'):
                        current_indent += char
                    else:
                        break
                
                # 为多行建议的每一行添加缩进
                if '\n' in suggestion:
                    lines = suggestion.split('\n')
                    adjusted_lines = [lines[0]]  # 第一行不需要额外缩进
                    for line in lines[1:]:
                        if line.strip():  # 非空行
                            adjusted_lines.append(current_indent + line)
                        else:
                            adjusted_lines.append(line)
                    suggestion = '\n'.join(adjusted_lines)
            
            # 保存状态
            self.state.suggestion_start_pos = cursor_pos
            self.state.current_suggestion = suggestion
            self.state.is_suggestion_active = True
            
            # 插入建议文本（带标签）
            self.text_widget.insert(cursor_pos, suggestion, (SUGGESTION_TAG,))
            
            # 计算结束位置
            self.state.suggestion_end_pos = self.text_widget.index("insert")
            
            # 将光标移回原位置
            self.text_widget.mark_set("insert", cursor_pos)
            
            logger.info(f"Suggestion shown: {len(suggestion)} chars at {cursor_pos}")
            return True
            
        except Exception as e:
            logger.error(f"Error showing suggestion: {e}")
            self.state.reset()
            return False
    
    def accept_suggestion(self) -> bool:
        """
        接受当前建议
        
        Returns:
            是否成功接受
        """
        if not self.state.is_suggestion_active:
            return False
            
        try:
            # 移除建议标签（保留文本）
            self.text_widget.tag_remove(
                SUGGESTION_TAG, 
                self.state.suggestion_start_pos, 
                self.state.suggestion_end_pos
            )
            
            # 将光标移到建议末尾
            self.text_widget.mark_set("insert", self.state.suggestion_end_pos)
            
            logger.info("Suggestion accepted")
            
            # 重置状态
            self.state.reset()
            return True
            
        except Exception as e:
            logger.error(f"Error accepting suggestion: {e}")
            self.state.reset()
            return False
    
    def hide_suggestion(self, delete_text: bool = True) -> bool:
        """
        隐藏（拒绝）当前建议
        
        Args:
            delete_text: 是否删除建议文本
            
        Returns:
            是否成功隐藏
        """
        if not self.state.is_suggestion_active:
            return False
            
        try:
            if delete_text and self.state.suggestion_start_pos and self.state.suggestion_end_pos:
                # 删除建议文本
                self.text_widget.delete(
                    self.state.suggestion_start_pos,
                    self.state.suggestion_end_pos
                )
            else:
                # 只移除标签
                self.text_widget.tag_remove(SUGGESTION_TAG, "1.0", "end")
            
            logger.info("Suggestion hidden/rejected")
            
            # 重置状态
            self.state.reset()
            return True
            
        except Exception as e:
            logger.error(f"Error hiding suggestion: {e}")
            self.state.reset()
            return False


class DebounceManager:
    """防抖管理器 - 防止快速重复触发"""
    
    def __init__(self, delay_ms: int = DEBOUNCE_DELAY_MS):
        self.delay_ms = delay_ms
        self.last_call_time = 0
        self.pending_timer = None
        self._lock = threading.Lock()
        
    def can_trigger(self) -> Tuple[bool, int]:
        """
        检查是否可以触发
        
        Returns:
            (can_trigger, remaining_ms) - 是否可以触发，剩余等待时间
        """
        current_time = time.time() * 1000
        elapsed = current_time - self.last_call_time
        
        if elapsed >= MIN_TRIGGER_INTERVAL_MS:
            return True, 0
        else:
            remaining = int(MIN_TRIGGER_INTERVAL_MS - elapsed)
            return False, remaining
    
    def record_trigger(self):
        """记录触发时间"""
        self.last_call_time = time.time() * 1000
    
    def debounce(self, callback, *args, **kwargs):
        """
        防抖执行
        
        Args:
            callback: 要执行的函数
            *args, **kwargs: 函数参数
        """
        with self._lock:
            # 取消之前的定时器
            if self.pending_timer:
                self.pending_timer.cancel()
            
            # 设置新的定时器
            self.pending_timer = threading.Timer(
                self.delay_ms / 1000.0,
                callback,
                args=args,
                kwargs=kwargs
            )
            self.pending_timer.start()
    
    def cancel_pending(self):
        """取消待执行的操作"""
        with self._lock:
            if self.pending_timer:
                self.pending_timer.cancel()
                self.pending_timer = None


class EdgeCaseHandler:
    """边缘情况处理器"""
    
    @staticmethod
    def handle_empty_file(text_widget) -> Dict[str, Any]:
        """处理空文件情况"""
        content = text_widget.get("1.0", "end-1c")
        if not content or content.isspace():
            return {
                "is_empty": True,
                "message": "File is empty. Start typing to get AI suggestions.",
                "can_complete": True  # 空文件也可以请求补全
            }
        return {"is_empty": False, "can_complete": True}
    
    @staticmethod
    def handle_large_file(text_widget, max_size: int = MAX_FILE_SIZE) -> Dict[str, Any]:
        """处理大文件情况"""
        content = text_widget.get("1.0", "end-1c")
        size = len(content)
        line_count = len(content.splitlines())
        
        if size > max_size:
            return {
                "is_large": True,
                "size": size,
                "line_count": line_count,
                "message": f"Large file detected ({line_count} lines, {size} chars). "
                          f"Only context around cursor will be used.",
                "can_complete": True,  # 仍然可以补全，但使用有限上下文
                "use_limited_context": True
            }
        return {
            "is_large": False,
            "size": size,
            "line_count": line_count,
            "can_complete": True
        }
    
    @staticmethod
    def validate_editor_state(editor) -> Dict[str, Any]:
        """验证编辑器状态"""
        try:
            if editor is None:
                return {
                    "valid": False,
                    "error": "no_editor",
                    "message": "No active editor. Please open a file first."
                }
            
            text_widget = editor.get_text_widget()
            if text_widget is None:
                return {
                    "valid": False,
                    "error": "no_text_widget",
                    "message": "Editor text widget not available."
                }
            
            # 检查编辑器是否可编辑
            state = text_widget.cget("state")
            if state == "disabled":
                return {
                    "valid": False,
                    "error": "editor_disabled",
                    "message": "Editor is read-only."
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": "validation_error",
                "message": f"Editor validation failed: {e}"
            }


# 导出便捷函数
def get_smart_context(text_widget) -> Dict[str, Any]:
    """获取智能上下文（便捷函数）"""
    return ContextExtractor.extract_context(text_widget)


def check_edge_cases(editor, text_widget) -> Dict[str, Any]:
    """检查所有边缘情况（便捷函数）"""
    result = {
        "can_complete": True,
        "warnings": [],
        "errors": []
    }
    
    # 验证编辑器
    editor_check = EdgeCaseHandler.validate_editor_state(editor)
    if not editor_check.get("valid"):
        result["can_complete"] = False
        result["errors"].append(editor_check.get("message"))
        return result
    
    # 检查空文件
    empty_check = EdgeCaseHandler.handle_empty_file(text_widget)
    if empty_check.get("is_empty"):
        result["warnings"].append(empty_check.get("message"))
        result["is_empty_file"] = True
    
    # 检查大文件
    large_check = EdgeCaseHandler.handle_large_file(text_widget)
    if large_check.get("is_large"):
        result["warnings"].append(large_check.get("message"))
        result["use_limited_context"] = True
        result["file_size"] = large_check.get("size")
        result["line_count"] = large_check.get("line_count")
    
    return result

