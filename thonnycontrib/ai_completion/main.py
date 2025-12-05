from thonny import get_workbench
from tkinter.messagebox import showinfo

def trigger_ai_completion(event=None):
    """
    触发 AI Completion 功能。
    event 参数是为了快捷键绑定时传入。
    """
    editor = get_workbench().get_editor_notebook().get_current_editor()
    if not editor:
        showinfo("AI Completion", "No active editor!")
        return

    text_widget = editor.get_text_widget()
    code = text_widget.get("1.0", "end-1c")

    showinfo("AI Completion", f"Dummy AI result.\n\nCurrent code:\n{code}")

def load_plugin():
    wb = get_workbench()

    # 注册菜单命令（显示在 Tools 菜单下）
    wb.add_command(
        command_id="ai_completion.trigger",
        menu_name="tools",
        command_label="AI Completion",
        handler=trigger_ai_completion,
        accelerator="Ctrl-Alt-A",  # 菜单显示快捷键
        group=100
    )

    # 绑定快捷键到当前编辑器（焦点在编辑器时生效）
    editor = wb.get_editor_notebook().get_current_editor()
    if editor:
        text_widget = editor.get_text_widget()
        text_widget.bind("<Control-Alt-a>", trigger_ai_completion)

    print("AI completion plugin loaded!")

