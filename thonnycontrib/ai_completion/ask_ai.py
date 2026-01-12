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

# ==================== TTS 模块 ====================
# 注意：不在模块加载时初始化，而是在需要时初始化
TTS_AVAILABLE = False
HAS_PYTTSX3 = False

# 检查 pyttsx3 是否可用
try:
    import pyttsx3

    HAS_PYTTSX3 = True
    TTS_AVAILABLE = True
    logger.info("✅ pyttsx3 模块可用")
except ImportError:
    logger.warning("⚠️ pyttsx3 未安装，语音功能不可用。请运行: pip install pyttsx3")


class TTSManager:
    """
    TTS 管理器 - 解决 pyttsx3 线程安全问题
    每次朗读都创建新的引擎实例，避免状态问题
    """

    def __init__(self):
        self.is_speaking = False
        self.should_stop = False
        self.engine = None
        self.lock = threading.Lock()

    def speak(self, text: str, callback=None):
        """
        朗读文本（在新线程中）

        Args:
            text: 要朗读的文本
            callback: 朗读完成后的回调函数
        """
        if not HAS_PYTTSX3:
            logger.warning("pyttsx3 can not be used")
            if callback:
                callback(False, "TTS can not be used")
            return False

        with self.lock:
            if self.is_speaking:
                logger.warning("Already reading aloud")
                return False
            self.is_speaking = True
            self.should_stop = False

        def speak_thread():
            success = False
            error_msg = ""

            try:
                # 每次都创建新的引擎实例（解决状态问题）
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)  # 语速
                engine.setProperty('volume', 1.0)  # 音量

                # 设置朗读完成的回调
                def on_end(name, completed):
                    pass

                engine.connect('finished-utterance', on_end)

                # 检查是否应该停止
                if not self.should_stop:
                    engine.say(text)
                    engine.runAndWait()
                    success = True

                # 清理引擎
                try:
                    engine.stop()
                except:
                    pass

            except Exception as e:
                error_msg = str(e)
                logger.error(f"TTS encountered a reading error: {e}")
            finally:
                with self.lock:
                    self.is_speaking = False
                    self.engine = None

                if callback:
                    callback(success, error_msg)

        # 启动朗读线程
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
        return True

    def stop(self):
        """停止朗读"""
        with self.lock:
            self.should_stop = True
            if self.engine:
                try:
                    self.engine.stop()
                except:
                    pass
            self.is_speaking = False

    @property
    def speaking(self):
        """是否正在朗读"""
        with self.lock:
            return self.is_speaking


class AskAIDialog:
    """Ask AI Everything 对话窗口"""

    def __init__(self, parent, ai_client_class):
        self.parent = parent
        self.ai_client_class = ai_client_class
        self.ai_client = None
        self.conversation_history = []
        self.last_response = ""

        # TTS 管理器
        self.tts = TTSManager()

        self._create_window()

    def _create_window(self):
        """创建对话窗口"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("🤖 Ask AI Everything")
        self.window.geometry("700x600")
        self.window.minsize(500, 400)

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
        tts_status = "🔊 Voice function is available" if TTS_AVAILABLE else "🔇 Voice function is unavailable (pip install pyttsx3)"
        tts_label = ttk.Label(title_frame, text=tts_status, foreground="gray")
        tts_label.pack(side=tk.RIGHT)

        # ========== 对话显示区域 ==========
        chat_frame = ttk.LabelFrame(main_frame, text="Dialogue", padding="5")
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

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

        self._append_message("system", "welcome using AI assistant！Ask me every thing.\nPrompt：Enter to send，Shift+Enter to start a new line\n")

        # ========== 输入区域 ==========
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

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

        self.input_text.bind("<Return>", self._on_enter)
        self.input_text.bind("<Shift-Return>", self._on_shift_enter)

        # 按钮区域
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.send_btn = ttk.Button(
            btn_frame,
            text="Send ➤",
            command=self._send_message,
            width=10
        )
        self.send_btn.pack(fill=tk.X, pady=(0, 5))

        self.speak_btn = ttk.Button(
            btn_frame,
            text="🔊 Read",
            command=self._toggle_speak,
            width=10,
            state=tk.NORMAL if TTS_AVAILABLE else tk.DISABLED
        )
        self.speak_btn.pack(fill=tk.X, pady=(0, 5))

        clear_btn = ttk.Button(
            btn_frame,
            text="🗑 Empty",
            command=self._clear_chat,
            width=10
        )
        clear_btn.pack(fill=tk.X)

        # ========== 底部状态栏 ==========
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X)

        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

        close_btn = ttk.Button(status_frame, text="Close", command=self._on_close)
        close_btn.pack(side=tk.RIGHT)

        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        self.window.bind("<Escape>", lambda e: self._on_close())

        self.window.transient(self.parent)
        self.window.grab_set()
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
        if not event.state & 0x1:
            self._send_message()
            return "break"
        return None

    def _on_shift_enter(self, event):
        """Shift+回车换行"""
        return None

    def _append_message(self, role: str, message: str):
        """添加消息到对话框"""
        self.chat_display.config(state=tk.NORMAL)

        timestamp = datetime.now().strftime("%H:%M:%S")

        if role == "user":
            self.chat_display.insert(tk.END, f"\n[{timestamp}] ", "time")
            self.chat_display.insert(tk.END, "You: ", "user")
            self.chat_display.insert(tk.END, f"{message}\n", "user_msg")
        elif role == "ai":
            self.chat_display.insert(tk.END, f"\n[{timestamp}] ", "time")
            self.chat_display.insert(tk.END, "AI: ", "ai")
            self.chat_display.insert(tk.END, f"{message}\n", "ai_msg")
        elif role == "error":
            self.chat_display.insert(tk.END, f"\n❌ Error: {message}\n", "error")
        elif role == "system":
            self.chat_display.insert(tk.END, f"{message}\n", "system")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _send_message(self):
        """发送消息"""
        message = self.input_text.get("1.0", tk.END).strip()

        if not message:
            return

        self.input_text.delete("1.0", tk.END)
        self._append_message("user", message)
        self.conversation_history.append({"role": "user", "content": message})

        self.send_btn.config(state=tk.DISABLED)
        self.status_label.config(text="🤔 AI is thinking...")

        thread = threading.Thread(target=self._request_ai, args=(message,), daemon=True)
        thread.start()

    def _request_ai(self, message: str):
        """发送 AI 请求（在后台线程）"""
        try:
            if self.ai_client is None:
                self.ai_client = self.ai_client_class()

            context = {
                "text": message,
                "prefix": self._build_conversation_context(),
                "suffix": "",
                "language": "general",
                "mode": "chat",
                "message": message,
                "history": self.conversation_history[-10:]
            }

            # 优先使用 request_chat 方法
            if hasattr(self.ai_client, 'request_chat'):
                result = self.ai_client.request_chat(context)
            else:
                # 兼容旧版 ai_client.py
                result = self.ai_client.request(context)

            self.window.after(0, lambda: self._handle_response(result))

        except Exception as e:
            logger.error(f"AI Request failed: {e}")
            self.window.after(0, lambda: self._handle_error(str(e)))

    def _build_conversation_context(self) -> str:
        """构建对话上下文"""
        context_parts = []
        for msg in self.conversation_history[-6:]:
            role = "User" if msg["role"] == "user" else "AI"
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
                self.status_label.config(text="✅ Answer completed")
                self.last_response = response
            else:
                self._append_message("error", "AI return empty response")
                self.status_label.config(text="⚠️ empty response")
        else:
            error_msg = result.get("message", "unknown error")
            self._append_message("error", error_msg)
            self.status_label.config(text=f"❌ {error_msg[:30]}...")

    def _handle_error(self, error: str):
        """处理错误"""
        self.send_btn.config(state=tk.NORMAL)
        self._append_message("error", error)
        self.status_label.config(text="❌ request failure")

    def _toggle_speak(self):
        """切换语音朗读"""
        if not TTS_AVAILABLE:
            self.status_label.config(text="⚠️ TTS is unaccessible，please deploy pyttsx3")
            return

        if self.tts.speaking:
            self._stop_speaking()
        else:
            self._start_speaking()

    def _start_speaking(self):
        """开始朗读最后一条 AI 回复"""
        if not self.last_response:
            self.status_label.config(text="⚠️ no content to read")
            return

        self.speak_btn.config(text="⏹ pause")
        self.status_label.config(text="🔊 reading...")

        def on_speak_done(success, error):
            """朗读完成回调（在主线程执行）"""

            def update_ui():
                self.speak_btn.config(text="🔊 read")
                if success:
                    self.status_label.config(text="✅ reading completed")
                elif error:
                    self.status_label.config(text=f"❌ reading failure: {error[:20]}")
                else:
                    self.status_label.config(text="⏹ paused")

            self.window.after(0, update_ui)

        # 使用 TTS 管理器朗读
        if not self.tts.speak(self.last_response, on_speak_done):
            self.speak_btn.config(text="🔊 read")
            self.status_label.config(text="⚠️ error in starting reading")

    def _stop_speaking(self):
        """停止朗读"""
        self.tts.stop()
        self.speak_btn.config(text="🔊 read")
        self.status_label.config(text="⏹ ended")

    def _clear_chat(self):
        """清空对话"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.conversation_history.clear()
        self.last_response = ""
        self._append_message("system", "conversation emptied，start a new conversation！\n")
        self.status_label.config(text="🗑 emptied")

    def _on_close(self):
        """关闭窗口"""
        self.tts.stop()
        self.window.destroy()


def open_ask_ai_dialog():
    """打开 Ask AI 对话框"""
    from thonny import get_workbench

    try:
        from .ai_client import AIClient
        wb = get_workbench()
        dialog = AskAIDialog(wb, AIClient)

    except ImportError as e:
        from tkinter import messagebox
        messagebox.showerror("error", f"unable to deploy AI customer module:\n{e}")
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror("error", f"open a new conversation:\n{e}")


if __name__ == "__main__":
    # 测试
    root = tk.Tk()
    root.withdraw()


    class MockAIClient:
        def request_chat(self, context):
            return {
                "success": True,
                "data": {
                    "raw_analysis": f"hello！you are asking：{context.get('message', '')}\n\nthis is a testing response。"
                }
            }


    dialog = AskAIDialog(root, MockAIClient)
    root.mainloop()
