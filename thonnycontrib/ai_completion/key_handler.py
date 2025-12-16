# key_handler.py
import tkinter as tk


class AIKeyHandler:
    """AI建议快捷键处理器"""

    def __init__(self, editor, ai_client):
        print("🤖 AIKeyHandler initializing...")

        self.editor = editor
        self.ai_client = ai_client
        self.text_widget = editor.get_text_widget()
        self.current_suggestion = None
        self.is_suggestion_active = False

        self._bind_keys()
        print("✅ AIKeyHandler initialized")

    def _bind_keys(self):
        """绑定快捷键"""
        widget = self.text_widget

        # 接受建议的快捷键
        widget.bind("<Return>", self._on_accept_suggestion, add=True)
        widget.bind("<KP_Enter>", self._on_accept_suggestion, add=True)
        widget.bind("<Tab>", self._on_accept_suggestion, add=True)

        # 拒绝建议的快捷键
        widget.bind("<Escape>", self._on_reject_suggestion, add=True)
        widget.bind("<Control-g>", self._on_reject_suggestion, add=True)

        print("⌨️ 快捷键绑定: Enter/Tab接受, Esc拒绝")

    def show_suggestion(self, suggestion, analysis_result=None):
        """
        显示AI建议到编辑器

        Args:
            suggestion: AI建议文本
            analysis_result: 可选的AI分析结果（用于提取元数据）
        """
        print("💡 Showing AI suggestion...")

        if not suggestion or suggestion.isspace():
            print("⚠️ 空建议，不显示")
            return

        self.current_suggestion = suggestion
        self.is_suggestion_active = True

        # 保存当前光标位置
        self.insert_position = self.text_widget.index("insert")

        print(f"📝 Suggestion length: {len(suggestion)} chars")
        print(f"📍 Insert position: {self.insert_position}")

        # 插入建议文本
        self.text_widget.insert(self.insert_position, suggestion, ("ai_suggestion",))

        # 配置建议文本的样式
        self.text_widget.tag_configure("ai_suggestion",
                                       background="#FFFFE0",
                                       foreground="#333333",
                                       underline=True,
                                       relief="ridge",
                                       borderwidth=1)

        # 选中建议文本
        end_pos = self.text_widget.index(f"{self.insert_position} + {len(suggestion)}c")
        self.text_widget.tag_add("sel", self.insert_position, end_pos)

        # 设置焦点
        self.text_widget.focus_set()

        print("✅ Suggestion displayed with highlighting")
        print("   Press Enter/Tab to accept, Esc to reject")

    def _on_accept_suggestion(self, event=None):
        """接受AI建议"""
        if not self.is_suggestion_active:
            return

        print("👍 Accepting suggestion")

        # 移除特殊标签
        self.text_widget.tag_remove("ai_suggestion", "1.0", "end")

        # 调用AI客户端的回调（如果有）
        if self.current_suggestion and hasattr(self.ai_client, 'on_suggestion_accepted'):
            try:
                self.ai_client.on_suggestion_accepted(self.current_suggestion)
            except Exception as e:
                print(f"调用on_suggestion_accepted时出错: {e}")

        # 重置状态
        self._reset_suggestion()

        print("✅ Suggestion accepted")
        return "break"

    def _on_reject_suggestion(self, event=None):
        """拒绝AI建议"""
        if not self.is_suggestion_active:
            return

        print("👎 Rejecting suggestion")

        # 删除建议文本
        if self.current_suggestion:
            try:
                # 尝试获取选中区域
                if self.text_widget.tag_ranges("sel"):
                    start = self.text_widget.index("sel.first")
                    end = self.text_widget.index("sel.last")
                    self.text_widget.delete(start, end)
            except Exception as e:
                print(f"删除建议文本时出错: {e}")

        # 调用AI客户端的回调（如果有）
        if self.current_suggestion and hasattr(self.ai_client, 'on_suggestion_rejected'):
            try:
                self.ai_client.on_suggestion_rejected(self.current_suggestion)
            except Exception as e:
                print(f"调用on_suggestion_rejected时出错: {e}")

        # 移除标签
        self.text_widget.tag_remove("ai_suggestion", "1.0", "end")

        # 重置状态
        self._reset_suggestion()

        print("✅ Suggestion rejected")
        return "break"

    def _reset_suggestion(self):
        """重置建议状态"""
        self.current_suggestion = None
        self.is_suggestion_active = False
        self.text_widget.tag_remove("ai_suggestion", "1.0", "end")

