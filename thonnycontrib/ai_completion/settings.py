# thonnycontrib/ai_completion/settings.py
"""
Settings Module - AI Code Completion Assistant
Provides settings dialog framework and menu integration
"""
import tkinter as tk
from tkinter import ttk, messagebox
from thonny import get_workbench
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Import other modules
try:
    from .ai_config import AICompletionConfig

    HAS_AI_CONFIG = True
    logger.info("✅ AICompletionConfig module imported")
except ImportError as e:
    HAS_AI_CONFIG = False
    logger.warning(f"⚠️ AICompletionConfig not found: {e}")

try:
    from .key_handler import AIKeyHandler

    HAS_KEY_HANDLER = True
    logger.info("✅ AIKeyHandler module imported")
except ImportError as e:
    HAS_KEY_HANDLER = False
    logger.warning(f"⚠️ AIKeyHandler not found: {e}")


class AISettingsManager:
    """AI Settings Manager"""

    def __init__(self):
        self.config = None
        self.key_handler = None
        self.workbench = get_workbench()

        # Team configuration
        self.team_config = {
            "team_name": "Group001",
            "default_endpoint": "https://api.microatp.com/v1/chat/completions",
            "default_model": "deepseek-chat"
        }

        # Initialize configuration
        if HAS_AI_CONFIG:
            try:
                self.config = AICompletionConfig()
                logger.info("✅ AICompletionConfig initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AICompletionConfig: {e}")

        # Initialize key handler (requires editor context)
        self._init_key_handler()

    def _init_key_handler(self, editor=None, ai_client=None):
        """Initialize key handler"""
        if HAS_KEY_HANDLER and editor and ai_client:
            try:
                self.key_handler = AIKeyHandler(editor, ai_client)
                logger.info("✅ AIKeyHandler initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize AIKeyHandler: {e}")

    def save_api_settings(self, api_key, endpoint, model):
        """Save API settings"""
        if not self.config:
            return False, "Configuration module not initialized"

        try:
            # Ensure api_settings section exists
            if "api_settings" not in self.config.config:
                self.config.config["api_settings"] = {}

            # Update API settings
            self.config.config["api_settings"]["api_key"] = api_key
            self.config.config["api_settings"]["endpoint"] = endpoint
            self.config.config["api_settings"]["model"] = model
            self.config.config["api_settings"]["last_updated"] = datetime.now().isoformat()

            # Save to config file
            success = self.config.save_config()

            if success:
                logger.info(f"✅ API settings saved: endpoint={endpoint}, model={model}")
                return True, "API settings saved successfully"
            else:
                logger.error("❌ API settings save failed")
                return False, "Failed to save configuration file"

        except Exception as e:
            error_msg = f"Error saving API settings: {e}"
            logger.error(error_msg)
            return False, error_msg

    def load_api_settings(self):
        """Load API settings"""
        if not self.config:
            # Return default configuration without API key
            return {
                "api_key": "",  # 需要用户配置
                "endpoint": self.team_config["default_endpoint"],
                "model": self.team_config["default_model"],
                "team_name": self.team_config["team_name"],
                "is_default": True
            }

        try:
            api_settings = self.config.config.get("api_settings", {})

            # If no saved settings, use defaults
            if not api_settings.get("endpoint"):
                return {
                    "api_key": api_settings.get("api_key", ""),  # 可能为空
                    "endpoint": self.team_config["default_endpoint"],
                    "model": api_settings.get("model", self.team_config["default_model"]),
                    "team_name": self.team_config["team_name"],
                    "is_default": True
                }

            return {
                "api_key": api_settings.get("api_key", ""),
                "endpoint": api_settings.get("endpoint", self.team_config["default_endpoint"]),
                "model": api_settings.get("model", self.team_config["default_model"]),
                "last_updated": api_settings.get("last_updated", ""),
                "is_default": False
            }
        except Exception as e:
            logger.error(f"Error loading API settings: {e}")
            return {
                "api_key": "",  # 出错时不暴露密钥
                "endpoint": self.team_config["default_endpoint"],
                "model": self.team_config["default_model"],
                "team_name": self.team_config["team_name"],
                "is_default": True
            }

    def show_config_status(self):
        """Show configuration status"""
        if not self.config:
            return "❌ Configuration not loaded"

        try:
            status = "✅ Current Configuration Status:\n\n"

            # Show API settings
            api_settings = self.config.config.get("api_settings", {})
            if api_settings:
                status += "🌐 API Settings:\n"
                for key, value in api_settings.items():
                    if key == "api_key" and value:
                        masked = "*" * 12 + value[-6:] if len(value) > 6 else "******"
                        status += f"  • {key}: {masked}\n"
                    elif key == "last_updated" and value:
                        try:
                            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            status += f"  • Last updated: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
                        except (ValueError, AttributeError):
                            status += f"  • {key}: {value}\n"
                    elif value:
                        status += f"  • {key}: {value}\n"
                status += "\n"

            # Show shortcut settings
            shortcuts = self.config.config.get("shortcuts", {})
            if shortcuts:
                status += "⌨️ Shortcut Settings:\n"
                for key, value in shortcuts.items():
                    if isinstance(value, list):
                        status += f"  • {key}: {', '.join(value)}\n"
                    else:
                        status += f"  • {key}: {value}\n"
                status += "\n"

            # Show AI settings
            ai_settings = self.config.config.get("ai_settings", {})
            if ai_settings:
                status += "🤖 AI Settings:\n"
                for key, value in ai_settings.items():
                    status += f"  • {key}: {value}\n"

            return status
        except Exception as e:
            return f"❌ Failed to get configuration: {e}"


def open_settings_dialog():
    """
    Open settings dialog
    """
    try:
        wb = get_workbench()

        # Create settings manager
        settings_manager = AISettingsManager()

        # Load existing API settings
        current_settings = settings_manager.load_api_settings()

        # Create dialog window
        dialog = tk.Toplevel(wb)
        dialog.title("AI Assistant Settings")
        dialog.geometry("550x500")

        # Allow vertical scaling
        dialog.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and status
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        title = ttk.Label(
            title_frame,
            text="AI Code Assistant Settings",
            font=("TkDefaultFont", 12, "bold")
        )
        title.pack(side=tk.LEFT)

        # Module status indicator
        status_frame = ttk.Frame(title_frame)
        status_frame.pack(side=tk.RIGHT)

        config_status = "✅" if HAS_AI_CONFIG else "❌"
        key_status = "✅" if HAS_KEY_HANDLER else "❌"

        ttk.Label(status_frame, text=f"Config: {config_status}").pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, text=f"KeyHandler: {key_status}").pack(side=tk.LEFT, padx=5)

        # Tab control
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 0: General Settings (新增)
        general_tab = ttk.Frame(notebook, padding="10")
        notebook.add(general_tab, text="General")
        
        # 启用/禁用开关
        enabled_var = tk.BooleanVar(value=settings_manager.config.is_enabled() if settings_manager.config else True)
        enabled_check = ttk.Checkbutton(
            general_tab, 
            text="Enable AI Code Assistant",
            variable=enabled_var
        )
        enabled_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 显示通知开关
        notify_var = tk.BooleanVar(value=True)
        notify_check = ttk.Checkbutton(
            general_tab,
            text="Show notifications",
            variable=notify_var
        )
        notify_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 上下文设置
        ttk.Label(general_tab, text="Context Settings:", font=("TkDefaultFont", 10, "bold")).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        context_config = settings_manager.config.get_context_config() if settings_manager.config else {}
        
        ttk.Label(general_tab, text="Lines before cursor:").grid(row=3, column=0, sticky=tk.W, pady=2)
        lines_before_var = tk.StringVar(value=str(context_config.get("lines_before", 50)))
        lines_before_entry = ttk.Entry(general_tab, width=10, textvariable=lines_before_var)
        lines_before_entry.grid(row=3, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(general_tab, text="Lines after cursor:").grid(row=4, column=0, sticky=tk.W, pady=2)
        lines_after_var = tk.StringVar(value=str(context_config.get("lines_after", 10)))
        lines_after_entry = ttk.Entry(general_tab, width=10, textvariable=lines_after_var)
        lines_after_entry.grid(row=4, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        ttk.Label(general_tab, text="Max context chars:").grid(row=5, column=0, sticky=tk.W, pady=2)
        max_chars_var = tk.StringVar(value=str(context_config.get("max_chars", 4000)))
        max_chars_entry = ttk.Entry(general_tab, width=10, textvariable=max_chars_var)
        max_chars_entry.grid(row=5, column=1, sticky=tk.W, pady=2, padx=(10, 0))
        
        # 说明文字
        ttk.Label(general_tab, 
                  text="💡 Tip: Smaller context = faster responses, larger context = better understanding",
                  foreground="gray").grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Tab 1: API Settings
        api_tab = ttk.Frame(notebook, padding="10")
        notebook.add(api_tab, text="API Settings")

        # API configuration fields
        ttk.Label(api_tab, text="API Key:", font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, pady=(0, 5))
        api_key_entry = ttk.Entry(api_tab, width=50, show="*")
        api_key_entry.grid(row=0, column=1, pady=(0, 5), padx=(10, 0))
        api_key_entry.insert(0, current_settings["api_key"])

        ttk.Label(api_tab, text="Endpoint:", font=("TkDefaultFont", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        endpoint_entry = ttk.Entry(api_tab, width=50)
        endpoint_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        endpoint_entry.insert(0, current_settings["endpoint"])

        ttk.Label(api_tab, text="Model:", font=("TkDefaultFont", 10, "bold")).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        model_entry = ttk.Entry(api_tab, width=50)
        model_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        model_entry.insert(0, current_settings["model"])

        # Last updated display
        if current_settings.get("last_updated"):
            try:
                dt = datetime.fromisoformat(current_settings["last_updated"].replace('Z', '+00:00'))
                last_updated_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                last_updated_str = current_settings["last_updated"]

            ttk.Label(api_tab, text="Last updated:", font=("TkDefaultFont", 9)).grid(
                row=3, column=0, sticky=tk.W, pady=(10, 0))
            ttk.Label(api_tab, text=last_updated_str, foreground="gray").grid(
                row=3, column=1, sticky=tk.W, pady=(10, 0), padx=(10, 0))

        # Tab 2: Configuration Status
        config_tab = ttk.Frame(notebook, padding="10")
        notebook.add(config_tab, text="Configuration")

        # Show configuration status
        if HAS_AI_CONFIG:
            config_text = tk.Text(config_tab, height=10, width=50, wrap=tk.WORD)
            config_text.grid(row=0, column=0, pady=5, sticky="nsew")

            config_scroll = ttk.Scrollbar(config_tab, orient=tk.VERTICAL, command=config_text.yview)
            config_scroll.grid(row=0, column=1, sticky="ns")
            config_text.config(yscrollcommand=config_scroll.set)

            config_text.insert(tk.END, settings_manager.show_config_status())
            config_text.config(state=tk.DISABLED)
        else:
            ttk.Label(config_tab, text="⚠️ Configuration module not available", foreground="orange").pack(pady=20)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))

        def save_settings():
            """Save settings manually"""
            try:
                # Get user input - General settings
                is_enabled = enabled_var.get()
                show_notify = notify_var.get()
                
                # Context settings
                try:
                    lines_before = int(lines_before_var.get())
                    lines_after = int(lines_after_var.get())
                    max_chars = int(max_chars_var.get())
                except ValueError:
                    messagebox.showwarning("Input Error", "Context settings must be numbers")
                    return
                
                # Get user input - API settings
                api_key = api_key_entry.get().strip()
                endpoint = endpoint_entry.get().strip()
                model = model_entry.get().strip()

                # Validate input
                if not endpoint:
                    messagebox.showwarning("Input Error", "Please enter API endpoint address")
                    endpoint_entry.focus_set()
                    return

                if not model:
                    messagebox.showwarning("Input Error", "Please enter model name")
                    model_entry.focus_set()
                    return

                # Show confirmation dialog
                confirm = messagebox.askyesno(
                    "Confirm Save",
                    f"Do you want to save these settings?\n\n"
                    f"AI Assistant: {'Enabled' if is_enabled else 'Disabled'}\n"
                    f"Team: {settings_manager.team_config['team_name']}\n"
                    f"Endpoint: {endpoint}\n"
                    f"Model: {model}\n"
                    f"Context: {lines_before} lines before, {lines_after} lines after\n\n"
                    f"Configuration will be saved to:\n"
                    f"{settings_manager.config.config_file if settings_manager.config else 'configuration file'}"
                )

                if not confirm:
                    return

                # Save general settings
                if settings_manager.config:
                    settings_manager.config.set_enabled(is_enabled)
                    settings_manager.config.set_context_config(
                        lines_before=lines_before,
                        lines_after=lines_after,
                        max_chars=max_chars
                    )

                # Save API settings
                success, message = settings_manager.save_api_settings(api_key, endpoint, model)

                if success:
                    # Verify save by reloading
                    saved_settings = settings_manager.load_api_settings()

                    verification_passed = (
                        saved_settings.get("endpoint") == endpoint and
                        saved_settings.get("model") == model
                    )

                    if verification_passed:
                        messagebox.showinfo(
                            "Save Successful",
                            f"✅ API Settings Saved Successfully!\n\n"
                            f"Team: {settings_manager.team_config['team_name']}\n"
                            f"Endpoint: {endpoint}\n"
                            f"Model: {model}\n\n"
                            f"Configuration saved to:\n"
                            f"{settings_manager.config.config_file if settings_manager.config else 'configuration file'}\n\n"
                            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                        logger.info(f"API settings saved successfully: {endpoint}, {model}")

                        # Update last updated time display
                        for widget in api_tab.winfo_children():
                            if isinstance(widget, ttk.Label) and widget.cget("text").startswith("Last updated:"):
                                widget.config(text=f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                break
                    else:
                        messagebox.showwarning(
                            "Save Verification Failed",
                            "Settings were saved but could not be verified.\n"
                            "Please check the configuration file manually."
                        )
                else:
                    messagebox.showerror("Save Failed", f"Failed to save settings: {message}")

            except Exception as e:
                error_msg = f"Error saving settings: {e}"
                logger.error(error_msg)
                messagebox.showerror("Error", error_msg)

        def test_connection():
            """Test API connection"""
            api_key = api_key_entry.get().strip()
            endpoint = endpoint_entry.get().strip()
            model = model_entry.get().strip()

            if not api_key:
                messagebox.showwarning("Input Required", "Please enter API Key first")
                api_key_entry.focus_set()
                return

            if not endpoint:
                messagebox.showwarning("Input Required", "Please enter API Endpoint first")
                endpoint_entry.focus_set()
                return

            # Show testing status
            test_btn.config(state=tk.DISABLED, text="⏳ Testing...")
            dialog.update()

            def do_test():
                try:
                    from .ai_client import AIClient
                    client = AIClient()
                    result = client.test_connection(api_key, endpoint, model)

                    # Show result in main thread
                    def show_result():
                        test_btn.config(state=tk.NORMAL, text="🔗 Test Connection")
                        if result.get("success"):
                            messagebox.showinfo(
                                "Connection Successful",
                                f"{result.get('message')}\n\n"
                                f"Endpoint: {endpoint}\n"
                                f"Model: {model}"
                            )
                        else:
                            messagebox.showerror(
                                "Connection Failed",
                                f"{result.get('message')}\n\n"
                                f"Please check:\n"
                                f"1. API Key is correct\n"
                                f"2. Endpoint URL is correct\n"
                                f"3. Network connection is available"
                            )

                    dialog.after(0, show_result)

                except Exception as e:
                    def show_error():
                        test_btn.config(state=tk.NORMAL, text="🔗 Test Connection")
                        messagebox.showerror("Error", f"Test failed:\n{e}")

                    dialog.after(0, show_error)

            # Run test in background thread to avoid blocking UI
            import threading
            threading.Thread(target=do_test, daemon=True).start()

        # Test Connection button (add before Save button)
        test_btn = ttk.Button(
            button_frame,
            text="🔗 Test Connection",
            command=test_connection,
            width=18
        )
        test_btn.pack(side=tk.LEFT, padx=5)
        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="💾 Save Settings",
            command=save_settings,
            width=15
        )
        save_btn.pack(side=tk.LEFT, padx=5)

        # Cancel button
        cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            width=10
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)

        # Set focus
        api_key_entry.focus_set()

        # Bind shortcuts
        dialog.bind('<Return>', lambda e: save_settings())
        dialog.bind('<Escape>', lambda e: dialog.destroy())

        # Make dialog modal
        dialog.transient(wb)
        dialog.grab_set()

        # Center dialog
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (wb.winfo_screenwidth() // 2) - (width // 2)
        y = (wb.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'+{x}+{y}')

        # Wait for dialog to close
        wb.wait_window(dialog)

        logger.info("Settings dialog opened")

    except Exception as e:
        logger.error(f"Failed to open settings dialog: {e}")
        messagebox.showerror("Error", f"Cannot open settings dialog: {e}")


def register_menu_items(workbench):
    """
    Register menu items to Thonny menu system
    """
    try:
        # Add separator
        try:
            workbench.add_separator("tools", 99)
        except Exception:
            pass

        # Add settings menu item
        workbench.add_command(
            command_id="ai_completion.settings",
            menu_name="tools",
            command_label="AI Assistant Settings...",
            handler=open_settings_dialog,
            default_sequence="<Control-Shift-A>",
            accelerator="Ctrl+Shift+A",
            group=101
        )

        logger.info("✅ Settings menu item registered")

        # Show integration status
        logger.info(f"Module integration - AI Config: {HAS_AI_CONFIG}, KeyHandler: {HAS_KEY_HANDLER}")

        return True

    except Exception as e:
        logger.error(f"Failed to register menu items: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


# Test function
def test_settings_module():
    """Test settings module"""
    print("Testing settings module...")

    try:
        # Create settings manager
        manager = AISettingsManager()

        print("=== Module Integration Test ===")
        print(f"✅ AI Configuration module available: {HAS_AI_CONFIG}")
        print(f"✅ Key Handler module available: {HAS_KEY_HANDLER}")
        print(f"✅ Team configuration: {manager.team_config['team_name']}")

        if HAS_AI_CONFIG and manager.config:
            print(f"✅ Configuration file path: {manager.config.config_file}")

            # Test API settings save (use placeholder for testing)
            test_result, message = manager.save_api_settings(
                "test-api-key-placeholder",  # 测试用占位符
                "https://api.microatp.com/v1/chat/completions",
                "deepseek-chat"
            )
            print(f"✅ API settings save test: {'Success' if test_result else 'Failed'} - {message}")

            # Test API settings load
            loaded = manager.load_api_settings()
            print(f"✅ API settings load test: {loaded.get('endpoint', 'N/A')}")

        return True
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


if __name__ == "__main__":
    print("Testing settings module...")


    # Mock workbench
    class MockWorkbench:
        def __init__(self):
            self.winfo_screenwidth = lambda: 1920
            self.winfo_screenheight = lambda: 1080


    mock_wb = MockWorkbench()

    # Test integration
    root = tk.Tk()
    root.withdraw()

    integration_test = test_settings_module()
    if integration_test:
        print("✅ Module integration test passed")
    else:
        print("❌ Module integration test failed")

    root.destroy()

