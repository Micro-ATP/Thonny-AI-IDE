# Introduction

## Ting Wang (14553505)
Hi, I am a senior year student majored in Intelligent Science and Technology, (joint degree from Coventry University and the Communication University of China), I am a self-motivated and strength-focused fast learner. My most familiar coding language is C/C++.
<br>
My homepage: https://rick-ting-wang.github.io

<!-- 在这里补充自己的信息 -->

## Manshu Li （14564040）
My name is Li Manshu. I'm proficient in Python and C++, and I'm inclined towards front-end engineering. I'm very willing to collaborate and communicate with everyone, to learn more knowledge. I hope we can have a pleasant cooperation.
<br>
My homepage:https://github.coventry.ac.uk/lim133

## Jin Qiao （14564464）
I'm Jin Qiao, a developer skilled in Python, Java, C#, C, C++. I also have experience with databases like MySQL and SQL. I enjoy building efficient solutions and look forward to collaboration.
<br>
My homepage:https://github.coventry.ac.uk/qiaoj3

## Siyuan Xu（14564132）
Hello, I am Xu Siyuan. I am skilled in Python, MySQL, and C. And I have some experience in machine learning projects, including house price prediction using linear regression. Hope we can cooperate well.
<br>
My homepage:https://github.coventry.ac.uk/xus29

## Lu Yanxi （14548947）

Hi, I am a programmer who prefers Rust and Python, and I usually write code with VSCode and Vim. I personally favor an Arch Linux environment for a highly customized workflow. I actively share my projects on my personal GitHub and contribute to our group’s development efforts.

My personal GitHub: https://github.com/Micro-ATP

Group GitHub: https://github.coventry.ac.uk/luy86

My blog: http://microatp.com
 (currently undergoing ICP registration, temporarily inaccessible)
 
# 🤖 AI Code Completion Plugin for Thonny（中英文对照 + 完整说明）

## 一、英文版本（可直接作为 GitHub README.md）
**GitHub Copilot-Style AI Code Completion Assistant**

[![Version](https://img.shields.io/badge/version-2.0.0--copilot-blue.svg)](https://github.com/your-repo)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Thonny](https://img.shields.io/badge/Thonny-4.0+-orange.svg)](https://thonny.org)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

---

## 📖 Project Overview

This plugin equips the **Thonny IDE** with GitHub Copilot-style AI-powered code completion, designed to enhance Python programming learning and development efficiency. By integrating large language model APIs, it delivers intelligent code completion, code analysis, and general-purpose AI Q&A capabilities.

> **Development Team**: Thonny-AI-Code-Completion-Group-1
> **Development Cycle**: Internship Project Sprints 1–3

---

## ✨ Key Features

### 🎯 Core Features (Developed During Internship)

#### 1. Ghost Text Completion
Inline code suggestion experience similar to GitHub Copilot:

- **Gray Italic Preview** — Suggested code appears in gray italics without disrupting regular coding workflows
- **Tab to Accept** — One-click acceptance of full suggestions
- **Esc to Cancel** — Quick dismissal of unwanted suggestions
- **Smart Indentation** — Automatic matching of current code indentation styles
- **Multi-line Support** — Completion for entire functions and code blocks
Input Example
def calculate_sum(|) ← Cursor Position
Ghost Text Display
def calculate_sum(numbers):
return sum(numbers) ← Gray Italic Suggestion
plaintext

#### 2. Intelligent Context Window
Provides the AI with precise code context:

| Configuration Item | Default Value | Description |
|--------------------|---------------|-------------|
| Lines Before Cursor | 50 | Ensures sufficient contextual information |
| Lines After Cursor | 10 | Facilitates code intent understanding |
| Maximum Characters | 4000 | Balances accuracy and performance |
| File Size Warning | 100KB | Automatic alerts for large files |

#### 3. Debounce Mechanism
Optimizes API calls for an improved user experience:

- **Debounce Delay**: 500ms — Avoids frequent triggering during active typing
- **Minimum Trigger Interval**: 1000ms — Prevents excessive API requests
- **Auto-Trigger**: Optional activation (disabled by default)

#### 4. Edge Case Handling
Robust exception management system:

- ✅ Empty file detection and prompts
- ✅ Intelligent sharding for large files
- ✅ Editor state validation
- ✅ Network timeout retries
- ✅ User-friendly API error prompts

#### 5. AI Client Module
Flexible API integration:

- Support for **OpenAI-compatible APIs** (DeepSeek, ChatGPT, etc.)
- **Completion Mode** — Intelligent code continuation
- **Analysis Mode** — Code quality assessment and recommendations
- **Response Filtering** — Automatic removal of irrelevant content from AI outputs

#### 6. Comprehensive Settings System
User-friendly configuration management:

- Graphical settings interface (`Ctrl+Shift+A`)
- Secure API key storage
- Configuration import/export functionality
- Customizable keyboard shortcuts

---

### 🌟 Additional Features (Extended Development)

#### 1. Ask AI Everything — General-Purpose AI Q&A

**Feature Description**:
Standalone AI chat window enabling queries on any topic, not limited to code-related questions.

**Key Features**:
- 🗨️ Multi-turn conversation support with contextual continuity
- 📜 Chat history management (most recent 6 rounds)
- 🎨 Dark theme interface for eye comfort
- ⌨️ Enter to send, Shift+Enter for line breaks
- 🔄 Chat clearing and reset options

**Usage**:
- Shortcut: `Ctrl+Alt+Q`
- Menu: Tools → Ask AI Everything...
┌─────────────────────────────────────────┐
│ 🤖 Ask AI Everything │
├─────────────────────────────────────────┤
│ │
│ [14:30:25] You: How to sort a dictionary in Python? │
│ │
│ [14:30:28] AI: You can use the sorted() function │
│ combined with a lambda expression: │
│ │
│ # Sort by keys │
│ sorted_dict = dict(sorted(d.items())) │
│ │
│ # Sort by values │
│ sorted_dict = dict(sorted(d.items(), │
│ key=lambda x: x[1]))│
│ │
├─────────────────────────────────────────┤
│ [Input Box...] [Send] [🔊 Read Aloud] │
└─────────────────────────────────────────┘
plaintext

#### 2. Accessibility Text-to-Speech (TTS) for Visually Impaired Users

**Feature Description**:
Provides text-to-speech functionality for AI responses to enable an accessible programming experience for visually impaired users.

**Key Features**:
- 🔊 One-click playback of AI responses
- ⏹️ Instant playback stopping
- 🎚️ Adjustable speaking rate (150 wpm by default)
- 🔒 Thread-safe implementation that does not block the interface
- 💻 Cross-platform support (Windows/macOS/Linux)

**Technical Implementation**:
```python
# pyttsx3-based TTS Manager
class TTSManager:
    def speak(self, text, callback=None):
        """Asynchronous speech synthesis with post-completion callback"""
        
    def stop(self):
        """Stop current speech playback"""
```      
        
Usage:
Retrieve AI responses in the Ask AI Everything window
Click the 🔊 Read Aloud button
Click again to stop playback
Dependency Installation:
```bash
pip install pyttsx3
```
🚀 Quick Start
System Requirements
Python: 3.8 or higher
Thonny: 4.0 or higher
Operating System: Windows / macOS / Linux
Installation Steps
Method 1: Manual Installation
Download Plugin Files
```bash
运行
git clone https://github.com/your-repo/thonny-ai-completion.git
```
Copy to Thonny Plugin Directory
Operating System	Plugin Directory Path
Windows	%APPDATA%\Thonny\plugins\
macOS	~/Library/Thonny/plugins/
Linux	~/.config/Thonny/plugins/
Install Dependencies
```bash
pip install requests pyttsx3
```
Restart Thonny
Method 2: Install via Thonny (Under Development)
plaintext
Tools → Manage plugins → Search for "ai-completion" → Install
API Configuration
Open Settings: Tools → AI Assistant Settings... or Ctrl+Shift+A
Fill in API Configuration:
Configuration Item	Example Value
API Key	sk-your-api-key-here
Endpoint	https://api.deepseek.com/v1/chat/completions
Model	deepseek-chat
Click Save Settings
⌨️ Shortcut Cheat Sheet
Function	Shortcut	Description
Trigger AI Completion	Ctrl+Alt+A	Manually request code completion
Accept Suggestion	Tab	Accept current Ghost Text
Reject Suggestion	Esc	Cancel current suggestion
Open Ask AI Everything	Ctrl+Alt+Q	Launch AI chat window
Open Settings	Ctrl+Shift+A	Configure API and preferences
Open Folder	Ctrl+Shift+O	Open project folder
📁 Project Structure
```plaintext
thonnycontrib/ai_completion/
│
├── __init__.py          # Plugin entry point and module imports
├── main.py              # Main module, Ghost Text implementation, plugin loading
├── ai_client.py         # AI client, API request handling
├── ai_config.py         # Configuration management and settings storage
├── completion_handler.py # Completion processing, context extraction, debounce mechanism
├── ghost_text.py        # Ghost Text manager (fallback implementation)
├── key_handler.py       # Keyboard shortcut handling
├── ask_ai.py            # Q&A chat functionality, TTS speech synthesis
├── settings.py          # Settings interface and menu integration
└── plugin_info.txt      # Plugin metadata
```
🔧 Configuration File
Configuration File Location:
Windows: %APPDATA%\Thonny\ai_completion\config.json
macOS/Linux: ~/.config/Thonny/ai_completion/config.json
Configuration Example:
json
{
  "general": {
    "enabled": true,
    "auto_trigger": false,
    "language": "en"
  },
  "shortcuts": {
    "trigger_ai": "Control-Alt-a",
    "accept_suggestion": ["Tab"],
    "reject_suggestion": ["Escape"]
  },
  "context": {
    "lines_before": 50,
    "lines_after": 10,
    "max_chars": 4000
  },
  "ai_service": {
    "provider": "openai_compatible",
    "api_key": "your-api-key",
    "endpoint": "https://api.deepseek.com/v1/chat/completions",
    "model": "deepseek-chat",
    "timeout": 30,
    "max_tokens": 500
  }
}
🛠️ Development Notes
Technology Stack
GUI: Tkinter (native to Thonny)
HTTP Client: requests
TTS Engine: pyttsx3
Configuration Management: JSON
Module Descriptions
Module	Responsibilities
main.py	Plugin entry point, core Ghost Text implementation
ai_client.py	API communication, response parsing, error handling
completion_handler.py	Context extraction, debounce control, edge case processing
ask_ai.py	Q&A chat functionality, TTS speech synthesis
settings.py	Settings interface, menu integration
Extension Development
Adding Support for New AI Providers:
```python
运行
# ai_client.py
class AIClient:
    def _make_api_request(self, context):
        # Add support for new API formats
        pass
```
📋 Version History
Version	Date	Updates
2.0.0-copilot	2024-XX	Ghost Text implementation, full system refactoring
1.0.0	2024-XX	Basic code completion functionality
0.1.0	2024-XX	Initial prototype
🤝 Contribution Guidelines
Issues and Pull Requests are welcome!
Fork this repository
Create a feature branch (git checkout -b feature/AmazingFeature)
Commit your changes (git commit -m 'Add AmazingFeature')
Push to the branch (git push origin feature/AmazingFeature)
Open a Pull Request
📄 License
This project is licensed under the MIT License — see the LICENSE file for details.
👥 Development Team
Thonny-AI-Code-Completion-Group-1
🙏 Acknowledgments
Thonny IDE — An excellent IDE for learning Python
DeepSeek — AI model support
pyttsx3 — Cross-platform TTS engine
<div align="center">
⭐ If this project helps you, please give it a Star! ⭐
</div>
