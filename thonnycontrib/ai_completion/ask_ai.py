"""
Ask AI Everything - 通用 AI 问答窗口
用户可以输入任何问题，获得 AI 回答，并支持语音朗读
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from logging import getLogger
from datetime import datetime

logger = getLogger(__name__)

# 尝试导入 TTS 模块
TTS_ENGINE = None
TTS_AVAILABLE = False


def init_tts():
    """初始化 TTS 引擎"""
    global TTS_ENGINE, TTS_AVAILABLE

    # 方法1: 尝试 pyttsx3（推荐，离线可用）
    try:
        import pyttsx3
        TTS_ENGINE = pyttsx3.init()
        # 设置语速（可调整）
        TTS_ENGINE.setProperty('rate', 150)
        TTS_AVAILABLE = True
        logger.info("✅ TTS 引擎初始化成功 (pyttsx3)")
        return True
    except Exception as e:
        logger.warning(f"pyttsx3 不可用: {e}")

    # 方法2: Windows 系统自带 TTS
    try:
        import platform
        if platform.system() == 'Windows':
            import win32com.client
            TTS_ENGINE = win32com.client.Dispatch("SAPI.SpVoice")
            TTS_AVAILABLE = True
            logger.info("✅ TTS 引擎初始化成功 (Windows SAPI)")
            return True
    except Exception as e:
        logger.warning(f"Windows SAPI 不可用: {e}")

    logger.warning("⚠️ TTS 功能不可用，请安装 pyttsx3: pip install pyttsx3")
    return False


# 尝试初始化 TTS
init_tts()


class AskAIDialog:
    """Ask AI Everything 对话窗口"""

    def __init__(self, parent, ai_client_class):
        self.parent = parent
        self.ai_client_class = ai_client_class
        self.ai_client = None
        self.is_speaking = False
        self.speak_thread = None
        self.conversation_history = []  # 保存对话历史

        self._create_window()

    def _create_window(self):
        """创建对话窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("🤖 Ask AI Everything")
        self.window.geometry("700x600")
        self.window.minsize(500, 400)

        # 设置窗口图标（如果可用）
        try:
            self.window.iconname("AI Assistant")
        except:
            pass

        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 顶部标题 ==========
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(
            title_frame,
            text="🤖 Ask AI Everything",
            font=("Arial", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)

        # TTS 状态标签
        tts_status = "🔊 语音可用" if TTS_AVAILABLE else "🔇 语音不可用"
        tts_label = ttk.Label(title_frame, text=tts_status, foreground="gray")
        tts_label.pack(side=tk.RIGHT)

        # ========== 对话显示区域 ==========
        chat_frame = ttk.LabelFrame(main_frame, text="对话", padding="5")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 对话文本框（带滚动条）
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            state=tk.DISABLED,
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="white"
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # 配置文本标签样式
        self.chat_display.tag_configure("user", foreground="#4FC3F7", font=("Arial", 11, "bold"))
        self.chat_display.tag_configure("ai", foreground="#81C784", font=("Arial", 11, "bold"))
        self.chat_display.tag_configure("user_msg", foreground="#E0E0E0")
        self.chat_display.tag_configure("ai_msg", foreground="#FFFFFF")
        self.chat_display.tag_configure("error", foreground="#EF5350")
        self.chat_display.tag_configure("system", foreground="#9E9E9E", font=("Arial", 9, "italic"))
        self.chat_display.tag_configure("time", foreground="#757575", font=("Arial", 8))

        # 添加欢迎消息
        self._append_message("system", "欢迎使用 AI 助手！你可以问我任何问题。\n提示：按 Enter 发送，Shift+Enter 换行\n")

        # ========== 输入区域 ==========
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # 输入文本框
        self.input_text = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#2d2d2d",
            fg="#ffffff",
            insertbackground="white"
        )
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.input_text.focus_set()

        # 绑定快捷键
        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)

        # 按钮区域
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # 发送按钮
        self.send_btn = ttk.Button(
            btn_frame,
            text="发送 ➤",
            command=self._send_message,
            width=10
        )
        self.send_btn.pack(fill=tk.X, pady=(0, 5))

        # 朗读按钮
        self.speak_btn = ttk.Button(
            btn_frame,
            text="🔊 朗读",
            command=self._toggle_speak,
            width=10,
            state=tk.NORMAL if TTS_AVAILABLE else tk.DISABLED
        )
        self.speak_btn.pack(fill=tk.X, pady=(0, 5))

        # 清空按钮
        clear_btn = ttk.Button(
            btn_frame,
            text="🗑 清空",
            command=self._clear_chat,
            width=10
        )
        clear_btn.pack(fill=tk.X)

        # ========== 底部状态栏 ==========
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="就绪", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        # 关闭按钮
        close_btn = ttk.Button(status_frame, text="关闭", command=self._on_close)
        close_btn.pack(side=tk.RIGHT)

        # 窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        # 快捷键
        self.window.bind("<Escape>", lambda e: self._on_close())

        # 使窗口模态
        self.window.transient(self.parent)
        self.window.grab_set()

        # 居中显示
        self._center_window()

    def _center_window(self):
        """将窗口居中"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"+{x}+{y}")

    def _on_enter(self, event):
        """回车发送消息"""
        if not event.state & 0x1:  # 没有按 Shift
            self._send_message()
            return "break"
        return None

    def _on_shift_enter(self, event):
        """Shift+回车换行"""
        return None  # 允许默认行为（换行）

    def _append_message(self, role: str, message: str):
        """添加消息到对话框"""
        self.chat_display.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")

        if role == "user":
            self.chat_display.insert(tk.END, f"\n[{timestamp}] ", "time")
            self.chat_display.insert(tk.END, "你: ", "user")
            self.chat_display.insert(tk.END, f"{message}\n", "user_msg")
        elif role == "ai":
            self.chat_display.insert(tk.END, f"\n[{timestamp}] ", "time")
            self.chat_display.insert(tk.END, "AI: ", "ai")
            self.chat_display.insert(tk.END, f"{message}\n", "ai_msg")
        elif role == "error":
            self.chat_display.insert(tk.END, f"\n❌ 错误: {message}\n", "error")
        elif role == "system":
            self.chat_display.insert(tk.END, f"{message}\n", "system")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)  # 滚动到底部

    def _send_message(self):
        """发送消息"""
        message = self.input_text.get("1.0", tk.END).strip()

        if not message:
            return

        # 清空输入框
        self.input_text.delete("1.0", tk.END)

        # 显示用户消息
        self._append_message("user", message)
        self.conversation_history.append({"role": "user", "content": message})

        # 禁用发送按钮
        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text="🤔 AI 正在思考...")

        # 在后台线程发送请求
        thread = threading.Thread(target=self._request_ai, args=(message,), daemon=True)
        thread.start()

    def _request_ai(self, message: str):
        """发送 AI 请求（在后台线程）"""
        try:
            # 创建 AI 客户端
            if self.ai_client is None:
                self.ai_client = self.ai_client_class()

            # 构建上下文（包含历史对话）
            context = {
                "text": message,
                "prefix": self._build_conversation_context(),
                "suffix": "",
                "language": "general",
                "mode": "chat",  # 聊天模式
                "message": message,
                "history": self.conversation_history[-10:]  # 最近10条对话
            }

            # 发送请求
            result = self.ai_client.request_chat(context)

            # 在主线程更新 UI
            self.window.after(0, lambda: self._handle_response(result))

        except Exception as e:
            logger.error(f"AI 请求失败: {e}")
            self.window.after(0, lambda: self._handle_error(str(e)))

    def _build_conversation_context(self) -> str:
        """构建对话上下文"""
        context_parts = []
        for msg in self.conversation_history[-6:]:  # 最近6条
            role = "用户" if msg["role"] == "user" else "AI"
            context_parts.append(f"{role}: {msg['content']}")
        return "\n".join(context_parts)

    def _handle_response(self, result: dict):
        """处理 AI 响应"""
        self.send_btn.config(state=tk.NORMAL)

        if result.get("success"):
            response = result.get("data", {}).get("raw_analysis", "")
            if response:
                self._append_message("ai", response)
                self.conversation_history.append({"role": "assistant", "content": response})
                self.status_label.config(text="✅ 回答完成")

                # 保存最后一条回复用于朗读
                self.last_response = response
            else:
                self._append_message("error", "AI 返回了空响应")
                self.status_label.config(text="⚠️ 空响应")
        else:
            error_msg = result.get("message", "未知错误")
            self._append_message("error", error_msg)
            self.status_label.config(text=f"❌ {error_msg[:30]}...")

    def _handle_error(self, error: str):
        """处理错误"""
        self.send_btn.config(state=tk.NORMAL)
        self._append_message("error", error)
        self.status_label.config(text="❌ 请求失败")

    def _toggle_speak(self):
        """切换语音朗读"""
        if not TTS_AVAILABLE:
            return

        if self.is_speaking:
            self._stop_speaking()
        else:
            self._start_speaking()

    def _start_speaking(self):
        """开始朗读最后一条 AI 回复"""
        if not hasattr(self, 'last_response') or not self.last_response:
            self.status_label.config(text="⚠️ 没有可朗读的内容")
            return

        self.is_speaking = True
        self.speak_btn.config(text="⏹ 停止")
        self.status_label.config(text="🔊 正在朗读...")

        # 在后台线程朗读
        self.speak_thread = threading.Thread(
            target=self._speak_text,
            args=(self.last_response,),
            daemon=True
        )
        self.speak_thread.start()

    def _speak_text(self, text: str):
        """朗读文本（在后台线程）"""
        global TTS_ENGINE

        try:
            if TTS_ENGINE is None:
                return

            # 检查引擎类型
            if hasattr(TTS_ENGINE, 'say'):
                # pyttsx3
                TTS_ENGINE.say(text)
                TTS_ENGINE.runAndWait()
            elif hasattr(TTS_ENGINE, 'Speak'):
                # Windows SAPI
                TTS_ENGINE.Speak(text)

        except Exception as e:
            logger.error(f"TTS 错误: {e}")
        finally:
            self.window.after(0, self._on_speak_finished)

    def _on_speak_finished(self):
        """朗读完成回调"""
        self.is_speaking = False
        self.speak_btn.config(text="🔊 朗读")
        self.status_label.config(text="✅ 朗读完成")

    def _stop_speaking(self):
        """停止朗读"""
        global TTS_ENGINE

        try:
            if TTS_ENGINE and hasattr(TTS_ENGINE, 'stop'):
                TTS_ENGINE.stop()
        except:
            pass

        self.is_speaking = False
        self.speak_btn.config(text="🔊 朗读")
        self.status_label.config(text="⏹ 已停止")

    def _clear_chat(self):
        """清空对话"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.conversation_history.clear()
        self._append_message("system", "对话已清空，开始新的对话吧！\n")
        self.status_label.config(text="🗑 已清空")

    def _on_close(self):
        """关闭窗口"""
        if self.is_speaking:
            self._stop_speaking()
        self.window.destroy()


def open_ask_ai_dialog():
    """打开 Ask AI 对话框"""
    from thonny import get_workbench

    try:
        # 导入 AI 客户端
        from .ai_client import AIClient

        # 创建对话框
        wb = get_workbench()
        dialog = AskAIDialog(wb, AIClient)

    except ImportError as e:
        from tkinter import messagebox
        messagebox.showerror("错误", f"无法加载 AI 客户端模块:\n{e}")
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("错误", f"打开对话框失败:\n{e}")


# ==================== 扩展 AIClient 支持聊天模式 ====================
def extend_ai_client():
    """
    扩展 AIClient 类，添加聊天功能
    需要在 ai_client.py 中添加 request_chat 方法
    """
    pass


if __name__ == "__main__":
    # 测试
    root = tk.Tk()
    root.withdraw()


    class MockAIClient:
        def request_chat(self, context):
            return {
                "success": True,
                "data": {
                    "raw_analysis": f"你好！你问的是：{context.get('message', '')}\n\n这是一个测试回复。"
                }
            }


    dialog = AskAIDialog(root, MockAIClient)
    root.mainloop()
