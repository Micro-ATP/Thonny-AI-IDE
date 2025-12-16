# Sprint 3 - Edge Cases Testing Documentation

## Overview
This document records the edge cases tested for Sprint 3 as per the Definition of Done requirements.

## Test Cases

### 1. Empty File
**Test Scenario:** Trigger AI completion in an empty editor

**Expected Behavior:**
- ✅ System detects empty file
- ✅ Logs warning "File is empty. Start typing to get AI suggestions."
- ✅ Still allows completion request (can suggest initial code structure)
- ✅ No crash or error dialog

**Status:** IMPLEMENTED
**Code Location:** `completion_handler.py` - `EdgeCaseHandler.handle_empty_file()`

---

### 2. Large File
**Test Scenario:** Trigger AI completion in a file > 100,000 characters

**Expected Behavior:**
- ✅ System detects large file
- ✅ Logs warning with file size information
- ✅ Uses limited context window (only lines around cursor)
- ✅ Does NOT send entire file to API
- ✅ Completion still works with reduced context

**Configuration:**
- `MAX_FILE_SIZE = 100000` characters
- `CONTEXT_LINES_BEFORE = 50` lines
- `CONTEXT_LINES_AFTER = 10` lines
- `MAX_CONTEXT_CHARS = 4000` characters

**Status:** IMPLEMENTED
**Code Location:** `completion_handler.py` - `EdgeCaseHandler.handle_large_file()`

---

### 3. Multiple Editors
**Test Scenario:** Open multiple files and switch between editors while using AI completion

**Expected Behavior:**
- ✅ Completion targets current active editor only
- ✅ Suggestion state resets when switching editors
- ✅ Inline suggestion manager recreated for new editor
- ✅ Key bindings properly installed per editor

**Status:** IMPLEMENTED
**Code Location:** `main.py` - `GlobalCompletionManager.get_or_create_inline_manager()`

---

### 4. Quickly Pressing Hotkey Multiple Times
**Test Scenario:** Rapidly press Ctrl+Alt+A multiple times

**Expected Behavior:**
- ✅ Debounce mechanism prevents rapid re-triggering
- ✅ Minimum interval: 1000ms between triggers
- ✅ Previous request state prevents concurrent requests
- ✅ Loading indicator shown/hidden properly
- ✅ No duplicate API calls

**Configuration:**
- `DEBOUNCE_DELAY_MS = 500` ms
- `MIN_TRIGGER_INTERVAL_MS = 1000` ms

**Status:** IMPLEMENTED
**Code Location:** 
- `completion_handler.py` - `DebounceManager`
- `main.py` - `trigger_ai_completion()` debounce check

---

### 5. Cursor at Different Positions
**Test Scenarios:**
- Beginning of file
- End of file
- Middle of line
- Empty line
- Inside function/class

**Expected Behavior:**
- ✅ Context extracted correctly for each position
- ✅ Indentation preserved when inserting suggestion
- ✅ Cursor position tracked accurately

**Status:** IMPLEMENTED
**Code Location:** `completion_handler.py` - `ContextExtractor.extract_context()`

---

### 6. Editor Not Ready
**Test Scenario:** Trigger completion before Thonny is fully loaded

**Expected Behavior:**
- ✅ Friendly error message: "Thonny is not ready yet"
- ✅ No crash
- ✅ Handles AssertionError from editor_notebook

**Status:** IMPLEMENTED
**Code Location:** `main.py` - `_do_completion()` try/except blocks

---

### 7. AI Assistant Disabled
**Test Scenario:** Disable AI Assistant in settings, then try to trigger

**Expected Behavior:**
- ✅ Shows message: "AI Assistant is disabled"
- ✅ Directs user to settings
- ✅ No API call made

**Status:** IMPLEMENTED
**Code Location:** `main.py` - `trigger_ai_completion()` enabled check

---

### 8. Read-Only Editor
**Test Scenario:** Try to insert suggestion in a read-only editor

**Expected Behavior:**
- ✅ Validates editor state before showing suggestion
- ✅ Shows appropriate error message

**Status:** IMPLEMENTED
**Code Location:** `completion_handler.py` - `EdgeCaseHandler.validate_editor_state()`

---

## Known Issues / Planned Improvements

### Issue 1: Multi-line Indentation
**Description:** Complex multi-line completions may not perfectly match all indentation styles
**Severity:** Low
**Plan:** Enhanced indentation detection in future sprint

### Issue 2: API Timeout
**Description:** Long API response times not yet handled with progress indicator
**Severity:** Medium  
**Plan:** Add timeout handling and progress bar

---

## Configuration Reference

| Setting | Default | Location |
|---------|---------|----------|
| `general.enabled` | `true` | Enable/disable AI assistant |
| `context.lines_before` | `50` | Lines before cursor in context |
| `context.lines_after` | `10` | Lines after cursor in context |
| `context.max_chars` | `4000` | Maximum context characters |
| `context.max_file_size` | `100000` | File size warning threshold |
| `completion.debounce_ms` | `500` | Debounce delay |
| `completion.min_trigger_interval_ms` | `1000` | Minimum trigger interval |

---

## Test Commands

```python
# Test in Thonny Shell:

# Check if AI is enabled
from thonnycontrib.ai_completion.ai_config import is_ai_enabled
print(f"AI Enabled: {is_ai_enabled()}")

# Check context extraction
from thonnycontrib.ai_completion.completion_handler import ContextExtractor
# (requires text_widget from editor)

# Check debounce
from thonnycontrib.ai_completion.completion_handler import DebounceManager
dm = DebounceManager()
print(dm.can_trigger())  # Should return (True, 0) first time
```

---

*Document Last Updated: Sprint 3*
*Author: AI Completion Group 1*

