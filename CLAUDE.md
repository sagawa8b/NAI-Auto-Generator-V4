# CLAUDE.md - AI Assistant Guide for NAI-Auto-V4

**Version:** V4.5_2.5.11.26
**Last Updated:** 2025-11-26
**Purpose:** Comprehensive guide for AI assistants working with the NAI-Auto-V4 codebase

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Codebase Structure](#codebase-structure)
3. [Architecture & Key Components](#architecture--key-components)
4. [Development Workflows](#development-workflows)
5. [Code Conventions](#code-conventions)
6. [Common Tasks & Patterns](#common-tasks--patterns)
7. [Testing & Debugging](#testing--debugging)
8. [Build & Distribution](#build--distribution)
9. [Important Files Reference](#important-files-reference)
10. [AI Assistant Guidelines](#ai-assistant-guidelines)

---

## Project Overview

### What is NAI-Auto-V4?

NAI-Auto-V4 is a **Windows desktop application** for automating image generation with Novel AI's diffusion models (V4/V4.5). It provides a PyQt5-based GUI for managing prompts, generating images, and utilizing advanced features like wildcards, character prompts, and image-to-image generation.

**Key Features:**
- Automated batch image generation with Novel AI API
- Multi-language support (Korean, English, Japanese, Chinese)
- Wildcard system for dynamic prompt generation
- Character prompt positioning system
- Image tagging using WD14 ONNX models
- Image-to-image and reference image support
- PNG metadata extraction and embedding
- Auto-completion for Danbooru tags

**Origin:**
- Forked from: https://github.com/DCP-arca/NAI-Auto-Generator
- Custom version with extensive V4/V4.5 enhancements

### Technology Stack

- **Language:** Python 3.x
- **GUI Framework:** PyQt5 >= 5.15.0
- **API Client:** requests >= 2.28.0
- **Image Processing:** Pillow >= 9.0.0
- **ML Inference:** onnxruntime == 1.13.1 (fixed for compatibility)
- **Cryptography:** argon2-cffi >= 21.3.0
- **Numerical:** numpy < 2 (constrained for onnxruntime compatibility)

### Codebase Statistics

- **Total Lines of Code:** ~10,200 lines
- **Core Modules:** 14 Python files
- **Languages:** 4 language files (JSON)
- **Main Entry Point:** `gui.py:4291-4298`

---

## Codebase Structure

### Directory Tree

```
NAI-Auto-V4/
├── Core Application Files
│   ├── gui.py                      (4,298 lines) - Main application window & logic
│   ├── gui_init.py                 (1,445 lines) - Widget initialization functions
│   ├── gui_dialog.py               (921 lines)   - Dialog windows (login, options, etc.)
│   └── character_prompts_ui.py     (648 lines)   - Character prompt UI components
│
├── API & Generation
│   ├── nai_generator.py            (970 lines)   - NovelAI API client & session manager
│   ├── naiinfo_getter.py           (128 lines)   - PNG metadata extraction
│   └── stealth_pnginfo.py          (116 lines)   - Hidden PNG metadata reader
│
├── Utilities & Processing
│   ├── wildcard_applier.py         (337 lines)   - Wildcard expansion engine
│   ├── danbooru_tagger.py          (159 lines)   - ONNX-based image tagging
│   ├── completer.py                (354 lines)   - Tag auto-completion system
│   └── i18n_manager.py             (437 lines)   - Internationalization manager
│
├── System & Configuration
│   ├── logger.py                   (203 lines)   - Unified logging system
│   ├── consts.py                   (165 lines)   - Constants & default parameters
│   └── installer_zipper.py         (27 lines)    - Distribution packaging
│
├── Data & Resources
│   ├── languages/                  - Translation JSON files
│   │   ├── ko.json                 - Korean (default)
│   │   ├── en.json                 - English
│   │   ├── ja.json                 - Japanese
│   │   └── zh.json                 - Chinese
│   ├── danbooru_tags_post_count.csv - Tag completion database
│   ├── app_icon.ico                - Application icon
│   └── icon.png                    - UI icon resource
│
├── Build & Distribution
│   ├── distribute.bat              - PyInstaller build script
│   └── requirements.txt            - Python dependencies
│
└── Documentation
    ├── README.md                   - Project overview (Korean)
    ├── credit.txt                  - Credits
    └── CLAUDE.md                   - This file
```

### File Responsibilities

| File | Primary Responsibility | Key Classes/Functions |
|------|----------------------|----------------------|
| `gui.py` | Main application window, event handling | `NAIAutoGeneratorWindow`, `NetworkMonitor` |
| `gui_init.py` | UI widget creation & initialization | `init_main_widget()`, layout functions |
| `gui_dialog.py` | Dialog windows | `LoginDialog`, `OptionDialog`, `GenerateDialog` |
| `character_prompts_ui.py` | Character prompt management | `CharacterPromptsContainer`, `CharacterPromptWidget` |
| `nai_generator.py` | NovelAI API client | `NAIGenerator`, `NAISessionManager` |
| `wildcard_applier.py` | Dynamic prompt expansion | `WildcardApplier` |
| `completer.py` | Tag auto-completion | `CompletionTextEdit`, `CustomCompleter` |
| `danbooru_tagger.py` | ML-based image tagging | `DanbooruTagger` |
| `i18n_manager.py` | Multi-language support | `I18nManager` (singleton) |
| `logger.py` | Centralized logging | `get_logger()`, `NAILogger` |
| `consts.py` | Configuration constants | `DEFAULT_PARAMS`, `RESOLUTION_FAMILIY`, `COLOR` |

---

## Architecture & Key Components

### Application Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  NAIAutoGeneratorWindow                  │
│                   (Main QMainWindow)                     │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  GUI Init    │  │   Dialogs    │  │  Character   │  │
│  │  (Widgets)   │  │   Windows    │  │   Prompts    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ NAIGenerator │  │   Wildcard   │  │  Completer   │  │
│  │   (API)      │  │   Applier    │  │   System     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Tagger     │  │    Logger    │  │    I18n      │  │
│  │  (ONNX ML)   │  │   System     │  │   Manager    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Core Classes

#### 1. NAIAutoGeneratorWindow (gui.py:288)

**Purpose:** Main application window orchestrating all UI components and business logic.

**Key Responsibilities:**
- Initialize application state and UI
- Handle user interactions via signals/slots
- Manage generation workflow
- Coordinate between API client and UI
- Handle settings persistence via QSettings

**Important Methods:**
```python
init_variable()           # Initialize variables, logger, i18n
init_window()             # Build UI layout
init_menubar()            # Create menus
init_statusbar()          # Create status bar
setup_layout_modes()      # Handle responsive layouts
apply_theme()             # Apply visual styling
login()                   # Authenticate with Novel AI
start_autogenerate()      # Begin auto-generation loop
generate_once()           # Generate single image
```

**Initialization Flow:**
```
QApplication → NAIAutoGeneratorWindow → init_variable()
                                     → init_window()
                                     → init_statusbar()
                                     → init_menubar()
                                     → show()
                                     → app.exec_()
```

#### 2. NAIGenerator (nai_generator.py:376)

**Purpose:** NovelAI API client handling authentication and image generation.

**Key Responsibilities:**
- Login/logout with Novel AI servers
- Validate and refresh authentication tokens
- Submit image generation requests
- Handle ANLAS (credit) queries
- Manage character prompts and positioning
- Support image-to-image and reference images

**Important Methods:**
```python
login(access_key)                    # Authenticate with API
logout()                             # Invalidate session
generate(params_dict)                # Generate image with parameters
validate_token()                     # Check token validity
get_anlas()                          # Query remaining credits
_refresh_token()                     # Renew authentication token
```

**API Endpoints:**
- Base URL: `https://image.novelai.net`
- Login: `/user/login`
- Generate: `/ai/generate-image`
- User info: `/user/information`

#### 3. NAISessionManager (nai_generator.py:22)

**Purpose:** Manages API session lifecycle with adaptive token refresh.

**Key Features:**
- Automatic token refresh scheduling
- Network connectivity monitoring
- Session health tracking
- Adaptive refresh intervals based on failure rates
- Session state persistence

**Important Methods:**
```python
start()                              # Begin session management
stop()                               # Stop background monitoring
set_access_key(key)                  # Update authentication key
_schedule_next_refresh()             # Plan next token refresh
_refresh_token()                     # Execute token renewal
_monitor_network()                   # Check network status
```

#### 4. WildcardApplier (wildcard_applier.py:9)

**Purpose:** Expand wildcard syntax in prompts for dynamic generation.

**Wildcard Syntax:**
```
__folder/file__           # Random selection from file
__folder/file[0]__        # Index-based selection
__folder/file[0-5]__      # Range selection
__folder/file{3}__        # Repeat counter (for loops)
```

**Important Methods:**
```python
apply_wildcards(text, snapshot_id)  # Expand wildcards in text
load_wildcards(folder)               # Load wildcard definitions
_get_wildcard_value(path, index)    # Resolve wildcard to value
```

**Wildcard File Format:**
```
# Comment lines start with #
option1
option2
option3
```

#### 5. CompletionTextEdit & CustomCompleter (completer.py)

**Purpose:** Provide Danbooru tag auto-completion in text fields.

**Key Features:**
- Context-aware tag suggestions
- Weighted tag ranking by popularity
- Real-time completion popup
- CSV-based tag database

**Important Methods:**
```python
# CompletionTextEdit
keyPressEvent(event)                 # Handle keyboard input
insertCompletion(completion)         # Insert selected tag

# CustomCompleter
update_completion(text)              # Update suggestions based on input
load_tags(csv_path)                  # Load tag database
```

**Tag Database:** `danbooru_tags_post_count.csv`
- Format: `tag_name,post_count`
- Sorted by popularity (post count)

#### 6. I18nManager (i18n_manager.py:8)

**Purpose:** Centralized internationalization (singleton pattern).

**Supported Languages:**
- Korean (ko) - Default
- English (en)
- Japanese (ja)
- Chinese (zh)

**Usage:**
```python
from i18n_manager import i18n, tr

# In code
label_text = tr("label_key")

# In UI
button.setText(tr("button_generate"))
```

**Translation File Structure:**
```json
{
  "language_name": "English",
  "language_code": "en",
  "translations": {
    "label_key": "Translated Text",
    "button_generate": "Generate"
  }
}
```

#### 7. DanbooruTagger (danbooru_tagger.py:46)

**Purpose:** Tag images using WD14 ONNX models.

**Supported Models:**
- wd-v1-4-moat-tagger-v2
- wd-v1-4-convnext-tagger-v2
- wd-v1-4-vit-tagger-v2

**Important Methods:**
```python
load_model(model_path)               # Load ONNX model
tag_image(image_path, threshold)     # Generate tags for image
_prepare_image(image)                # Preprocess image for model
```

**Model Storage:** `./models/` directory

### Worker Threads

**Purpose:** Prevent UI freezing during long-running operations.

**Available Threads:**
- `CompletionTagLoadThread` - Load tag database asynchronously
- `AutoGenerateThread` - Run auto-generation loop
- `GenerateThread` - Generate single image
- `TokenValidateThread` - Validate API token
- `AnlasThread` - Fetch ANLAS credits
- `LoginThread` - Handle login process
- `WorkerThread` - Generic background operations

**Pattern:**
```python
class MyThread(QThread):
    result_signal = pyqtSignal(object)

    def run(self):
        # Long-running operation
        result = do_work()
        self.result_signal.emit(result)

# Usage in main window
thread = MyThread()
thread.result_signal.connect(self.handle_result)
thread.start()
```

### Signal-Slot Architecture

**PyQt5 Event System:**
```python
# Define signal
class MyClass(QObject):
    my_signal = pyqtSignal(str, int)

# Emit signal
self.my_signal.emit("message", 42)

# Connect to slot
self.my_signal.connect(self.my_handler)

# Handler method
def my_handler(self, message, value):
    print(f"{message}: {value}")
```

**Common Signals in Codebase:**
- `result_signal` - Thread completion
- `progress_signal` - Progress updates
- `error_signal` - Error notifications
- `network_status_changed` - Network connectivity
- `token_refreshed` - Authentication renewal

---

## Development Workflows

### Git Workflow

**Current Branch:** `claude/update-claude-md-014n3pb83kg1DtBFS6YR8aqF`

**Branch Naming Convention:**
- Feature branches: `claude/<description>-<session-id>`
- All development should occur on designated branch
- Push to remote: `git push -u origin <branch-name>`

**Recent Development Activity:**
```
3dd1f3e Drag&Drop Update
3d3226a Merge pull request #22 (fix-prompt-display)
0b80b0c ver up
3e2dfd4 Improve character prompt display and result text visibility
a1851cb Merge pull request #21 (add-colon-emphasis-syntax)
```

**Commit Guidelines:**
- Use descriptive commit messages
- Focus on "why" rather than "what"
- Follow existing commit style (concise, functional descriptions)
- Commit types: ver update, UI update, feature update, bug fix

### Development Environment Setup

**Prerequisites:**
```bash
# Python 3.x with pip
python --version  # Should be 3.7+

# Install dependencies
pip install -r requirements.txt
```

**Running the Application:**
```bash
# From repository root
python gui.py

# With debug logging (set in logger.py)
# Set DEBUG = True in logger.py
python gui.py
```

**Directory Structure for Runtime:**
```
NAI-Auto-V4/
├── results/          # Generated images (created automatically)
├── settings/         # Saved settings (created automatically)
├── wildcards/        # Wildcard definition files
├── models/           # ONNX tagger models
└── logs/             # Application logs
```

### Adding New Features

**Typical Workflow:**

1. **Planning:**
   - Identify affected modules
   - Consider UI impact
   - Plan data flow
   - Check internationalization needs

2. **Implementation:**
   - Add constants to `consts.py` if needed
   - Create utility classes in separate files
   - Update `gui_init.py` for new widgets
   - Modify `gui.py` for event handling
   - Add translations to `languages/*.json`

3. **Integration:**
   - Connect signals/slots
   - Update worker threads if async needed
   - Add logging statements
   - Update settings persistence

4. **Testing:**
   - Manual testing via GUI
   - Check all language variants
   - Test with different settings
   - Verify PyInstaller build works

### Making UI Changes

**Location:** `gui_init.py` for widgets, `gui.py` for logic

**Pattern:**
```python
# In gui_init.py - Create widget
def init_my_widget(parent):
    """Widget initialization function"""
    widget = QWidget()
    layout = QVBoxLayout()

    # Create components
    label = QLabel(tr("my_label"))
    button = QPushButton(tr("my_button"))

    # Arrange layout
    layout.addWidget(label)
    layout.addWidget(button)
    widget.setLayout(layout)

    return widget, button  # Return interactive elements

# In gui.py - Use widget in main window
def init_window(self):
    my_widget, my_button = init_my_widget(self)
    self.my_button = my_button  # Store reference
    self.my_button.clicked.connect(self.on_my_button_clicked)

def on_my_button_clicked(self):
    """Event handler"""
    logger.info("Button clicked")
    # Handle event
```

**Styling:**
```python
# Apply custom colors (from consts.COLOR)
button.setStyleSheet(f"background-color: {COLOR.BUTTON_CUSTOM}")

# Apply theme
self.apply_theme()  # Re-applies current theme
```

### Adding API Features

**Location:** `nai_generator.py`

**Pattern:**
```python
class NAIGenerator:
    def my_new_api_call(self, params):
        """New API endpoint call"""
        try:
            logger.info(f"Calling new endpoint: {params}")

            # Prepare request
            url = f"{self.base_url}/new-endpoint"
            headers = {"Authorization": f"Bearer {self.token}"}
            data = self._prepare_data(params)

            # Make request
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=30
            )

            # Handle response
            if response.status_code == 200:
                result = response.json()
                logger.info("API call successful")
                return result
            else:
                logger.error(f"API error: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Exception in API call: {e}")
            return None
```

### Adding Translations

**Location:** `languages/*.json`

**Process:**
1. Add key-value pair to all language files
2. Use `tr()` function in code
3. Test with each language setting

**Example:**
```json
// languages/en.json
{
  "language_name": "English",
  "language_code": "en",
  "translations": {
    "my_new_feature": "My New Feature",
    "my_new_button": "Click Me"
  }
}

// languages/ko.json
{
  "language_name": "한국어",
  "language_code": "ko",
  "translations": {
    "my_new_feature": "새로운 기능",
    "my_new_button": "클릭하세요"
  }
}
```

```python
# In code
label.setText(tr("my_new_feature"))
button.setText(tr("my_new_button"))
```

---

## Code Conventions

### Naming Conventions

**Classes:** PascalCase
```python
class NAIAutoGeneratorWindow(QMainWindow):
class WildcardApplier:
class CustomCompleter(QCompleter):
```

**Functions & Methods:** snake_case
```python
def init_main_widget():
def apply_wildcards(text):
def _refresh_token():  # Leading underscore for private
```

**Constants:** UPPER_CASE
```python
DEFAULT_PARAMS = {...}
MAX_COUNT_FOR_WHILE = 10
BASE_URL = "https://image.novelai.net"
```

**Variables:** snake_case
```python
image_path = "./results/image.png"
token_valid = True
user_settings = QSettings()
```

**Private Members:** Leading underscore
```python
self._token = None
self._session_manager = None
def _internal_method(self):
```

### Import Organization

**Standard Pattern:**
```python
# 1. Standard library imports
import json
import sys
import os
from io import BytesIO

# 2. Third-party imports
import requests
from PIL import Image
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal

# 3. Local imports
from consts import DEFAULT_PARAMS, COLOR
from logger import get_logger
from i18n_manager import tr
```

### Error Handling

**File Operations:**
```python
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    data = None
except json.JSONDecodeError as e:
    logger.error(f"JSON decode error: {e}")
    data = None
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    data = None
```

**Network Operations:**
```python
try:
    response = requests.post(url, json=data, timeout=30)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"HTTP {response.status_code}: {response.text}")
        return None
except requests.exceptions.Timeout:
    logger.error("Request timeout")
    return None
except requests.exceptions.RequestException as e:
    logger.error(f"Network error: {e}")
    return None
```

**User Notifications:**
```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    QMessageBox.critical(
        self,
        tr("error_title"),
        tr("error_message") + f"\n{str(e)}"
    )
```

### Logging Practices

**Logger Initialization:**
```python
from logger import get_logger
logger = get_logger()
```

**Log Levels:**
```python
logger.debug("Detailed debug information")  # DEBUG level only
logger.info("General information")           # Always logged
logger.warning("Warning message")            # Potential issues
logger.error("Error occurred")               # Actual errors
```

**Logging Best Practices:**
- Log important state changes
- Log API calls and responses
- Log file operations
- Log user actions (generation, login, etc.)
- Include context in log messages
- Use Korean or English for log messages (both acceptable)

### Code Comments

**Language:** Mixed Korean and English (Korean more common)

**Documentation Style:**
```python
def apply_wildcards(self, text, snapshot_id=None):
    """
    Apply wildcard expansion to text.

    Args:
        text (str): Text containing wildcard syntax
        snapshot_id (int, optional): Snapshot ID for consistency

    Returns:
        str: Text with wildcards expanded
    """
    # 구현 로직...
```

**Inline Comments:**
```python
# 한국어 주석 예시 (Korean comment example)
if seed == -1:
    seed = random.randint(0, 2**32 - 1)  # 랜덤 시드 생성

# English comment example
token = self._refresh_token()  # Renew authentication
```

### Resource Path Handling

**Pattern for PyInstaller Compatibility:**
```python
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running in normal Python environment
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Usage
icon_path = resource_path("app_icon.ico")
csv_path = resource_path("danbooru_tags_post_count.csv")
```

### Settings Persistence

**Using QSettings:**
```python
# Initialize
settings = QSettings(TOP_NAME, APP_NAME)

# Save setting
settings.setValue("key_name", value)

# Load setting with default
value = settings.value("key_name", default_value)

# Save complex types
settings.setValue("window_geometry", self.saveGeometry())
settings.setValue("window_state", self.saveState())

# Load complex types
self.restoreGeometry(settings.value("window_geometry"))
self.restoreState(settings.value("window_state"))
```

---

## Common Tasks & Patterns

### Task 1: Adding a New Parameter

**Steps:**

1. **Add to `consts.py`:**
```python
DEFAULT_PARAMS = {
    # ... existing params ...
    "my_new_param": "default_value",
}
```

2. **Add UI Control in `gui_init.py`:**
```python
def init_my_param_widget(parent):
    widget = QWidget()
    layout = QHBoxLayout()

    label = QLabel(tr("my_new_param_label"))
    input_field = QLineEdit("default_value")

    layout.addWidget(label)
    layout.addWidget(input_field)
    widget.setLayout(layout)

    return widget, input_field
```

3. **Integrate in `gui.py`:**
```python
# In init_window()
my_param_widget, self.my_param_input = init_my_param_widget(self)
main_layout.addWidget(my_param_widget)

# In parameter collection method
def get_params(self):
    params = {
        # ... existing params ...
        "my_new_param": self.my_param_input.text(),
    }
    return params
```

4. **Add to API Call in `nai_generator.py`:**
```python
def generate(self, params_dict):
    # ... existing code ...
    data["my_new_param"] = params_dict.get("my_new_param", "default")
```

5. **Add Translations:**
```json
// languages/en.json
"my_new_param_label": "My New Parameter"

// languages/ko.json
"my_new_param_label": "새 매개변수"
```

### Task 2: Adding a Dialog Window

**Pattern:**

1. **Create Dialog Class in `gui_dialog.py`:**
```python
class MyCustomDialog(QDialog):
    """Custom dialog for specific task"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("dialog_title"))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Add widgets
        self.input_field = QLineEdit()
        self.ok_button = QPushButton(tr("ok"))
        self.cancel_button = QPushButton(tr("cancel"))

        # Connect signals
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        # Arrange layout
        layout.addWidget(QLabel(tr("prompt")))
        layout.addWidget(self.input_field)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_value(self):
        """Return dialog result"""
        return self.input_field.text()
```

2. **Use Dialog in `gui.py`:**
```python
def open_my_dialog(self):
    dialog = MyCustomDialog(self)
    if dialog.exec_() == QDialog.Accepted:
        value = dialog.get_value()
        logger.info(f"Dialog result: {value}")
        # Process result
    else:
        logger.info("Dialog cancelled")
```

### Task 3: Adding Background Task

**Pattern:**

1. **Create Thread Class:**
```python
class MyWorkerThread(QThread):
    """Background worker for long operation"""

    # Define signals
    progress_signal = pyqtSignal(int)
    result_signal = pyqtSignal(object)
    error_signal = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        """Main thread execution"""
        try:
            logger.info("Worker thread started")

            # Long-running operation
            for i in range(100):
                # Do work
                result = self.do_work_step(i)

                # Report progress
                self.progress_signal.emit(i)

                # Check for interruption
                if self.isInterruptionRequested():
                    logger.info("Thread interrupted")
                    return

            # Emit result
            final_result = self.finalize()
            self.result_signal.emit(final_result)

        except Exception as e:
            logger.error(f"Thread error: {e}")
            self.error_signal.emit(str(e))

    def do_work_step(self, step):
        """Individual work step"""
        # Implementation
        pass
```

2. **Use Thread in Main Window:**
```python
def start_background_task(self):
    """Launch background operation"""
    # Create thread
    self.worker_thread = MyWorkerThread(self.get_params())

    # Connect signals
    self.worker_thread.progress_signal.connect(self.update_progress)
    self.worker_thread.result_signal.connect(self.handle_result)
    self.worker_thread.error_signal.connect(self.handle_error)

    # Start thread
    self.worker_thread.start()

    # Update UI
    self.start_button.setEnabled(False)
    self.stop_button.setEnabled(True)

def update_progress(self, value):
    """Update progress bar"""
    self.progress_bar.setValue(value)

def handle_result(self, result):
    """Process thread result"""
    logger.info(f"Task completed: {result}")
    self.start_button.setEnabled(True)
    self.stop_button.setEnabled(False)

def handle_error(self, error_msg):
    """Handle thread error"""
    QMessageBox.critical(self, tr("error"), error_msg)
    self.start_button.setEnabled(True)
    self.stop_button.setEnabled(False)

def stop_background_task(self):
    """Stop running thread"""
    if self.worker_thread and self.worker_thread.isRunning():
        self.worker_thread.requestInterruption()
        self.worker_thread.wait()  # Wait for clean shutdown
```

### Task 4: Adding Wildcard Support

**Wildcard File Structure:**
```
wildcards/
├── characters/
│   ├── female.txt
│   └── male.txt
├── styles/
│   ├── anime.txt
│   └── realistic.txt
└── colors/
    └── hair.txt
```

**Wildcard File Content (Example: `wildcards/characters/female.txt`):**
```
# Female character archetypes
magical girl
warrior princess
detective
scientist
artist
```

**Usage in Prompts:**
```
# Random selection
1girl, __characters/female__, __colors/hair__ hair

# Index-based (first item)
1girl, __characters/female[0]__, blue eyes

# Range selection
1girl, __characters/female[0-2]__, standing

# With repeat counter (for auto-generation loops)
1girl, __characters/female{3}__, smiling
```

**Implementation:**
```python
# Apply wildcards before generation
from wildcard_applier import WildcardApplier

applier = WildcardApplier()
applier.load_wildcards("./wildcards/")

original_prompt = "1girl, __characters/female__, __colors/hair__ hair"
expanded_prompt = applier.apply_wildcards(original_prompt)
# Result: "1girl, magical girl, blonde hair"
```

### Task 5: Working with PNG Metadata

**Reading Metadata:**
```python
import naiinfo_getter

# Extract metadata from PNG
metadata = naiinfo_getter.read_info_from_image("image.png")

if metadata:
    print(f"Prompt: {metadata['prompt']}")
    print(f"Model: {metadata['model']}")
    print(f"Seed: {metadata['seed']}")
```

**Writing Metadata:**
```python
from PIL import Image
from PIL.PngImagePlugin import PngInfo

# Load image
image = Image.open("input.png")

# Create metadata
pnginfo = PngInfo()
pnginfo.add_text("Title", "NAI Metadata")
pnginfo.add_text("Description", json.dumps(params_dict))
pnginfo.add_text("Comment", prettify_naidict(params_dict))

# Save with metadata
image.save("output.png", pnginfo=pnginfo)
```

---

## Testing & Debugging

### Manual Testing

**No formal test framework** - testing is primarily manual through GUI.

**Testing Checklist:**
- [ ] Login/logout functionality
- [ ] Single image generation
- [ ] Auto-generation loop
- [ ] Wildcard expansion
- [ ] Character prompts
- [ ] Image-to-image generation
- [ ] Reference image support
- [ ] Tag auto-completion
- [ ] Image tagging (ONNX)
- [ ] Multi-language UI
- [ ] Settings persistence
- [ ] Network error handling
- [ ] Token refresh
- [ ] ANLAS display

### Debugging

**Enable Debug Logging:**

Edit `logger.py`:
```python
# Change DEBUG setting
DEBUG = True  # Enable verbose logging
```

**Log Location:**
- Default: `~/NAI-Auto-Generator/logs/`
- Filename format: `nai_generator_YYYYMMDD.log`
- Rotating logs: 10MB per file, automatic rotation

**Log Output:**
```
2025-11-14 10:30:15 - INFO - Login successful
2025-11-14 10:30:16 - DEBUG - Token: eyJ0eXAi...
2025-11-14 10:30:20 - INFO - Generating image with seed: 12345
2025-11-14 10:30:25 - ERROR - API error: 401 Unauthorized
```

**Common Issues & Solutions:**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Token invalid" | Expired authentication | Click login button again |
| "ANLAS insufficient" | Low credits | Check subscription status |
| Network timeout | Slow connection | Increase timeout in requests |
| Wildcard not expanded | File path wrong | Check `./wildcards/` folder |
| UI freeze | Blocking operation | Use QThread for long tasks |
| Image not saved | Folder missing | Call `create_folder_if_not_exists()` |
| Translation missing | Key not in JSON | Add to all language files |

**Debugging Tips:**

1. **Check Logs First:**
   ```python
   logger.info(f"Current state: {variable}")
   logger.debug(f"Detailed info: {json.dumps(data, indent=2)}")
   ```

2. **Verify API Responses:**
   ```python
   logger.info(f"Response status: {response.status_code}")
   logger.debug(f"Response body: {response.text}")
   ```

3. **Trace Signal/Slot Connections:**
   ```python
   @pyqtSlot()
   def my_slot(self):
       logger.info("Slot triggered")  # Confirm connection works
   ```

4. **Monitor Thread Lifecycle:**
   ```python
   def run(self):
       logger.info("Thread started")
       # ... work ...
       logger.info("Thread completed")
   ```

5. **Validate User Input:**
   ```python
   value = self.input_field.text()
   logger.debug(f"User input: '{value}' (type: {type(value)})")
   ```

---

## Build & Distribution

### Build Script

**File:** `distribute.bat`

**Purpose:** Create Windows executable using PyInstaller

**Process:**
```batch
REM Build onefile version
pyinstaller --onefile --noconsole --name="NAI_Auto_V4" ^
    --icon=app_icon.ico ^
    --add-data="danbooru_tags_post_count.csv;." ^
    --add-data="icon.png;." ^
    gui.py

REM Build directory version
pyinstaller --noconsole --name="NAI_Auto_V4" ^
    --icon=app_icon.ico ^
    --add-data="danbooru_tags_post_count.csv;." ^
    --add-data="icon.png;." ^
    gui.py
```

**Output Locations:**
- Onefile: `dist_onefile/NAI_Auto_V4.exe`
- Directory: `dist/NAI_Auto_V4/`

**Build Requirements:**
```bash
pip install pyinstaller
```

**Building Process:**

1. **Ensure all dependencies installed:**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

2. **Run build script:**
   ```bash
   distribute.bat
   ```

3. **Test executable:**
   - Run from `dist/` or `dist_onefile/`
   - Test all features
   - Check resource loading

4. **Create distribution package:**
   - ZIP the `dist/` folder
   - Include README.md
   - Include credit.txt

### Distribution Checklist

- [ ] All dependencies in `requirements.txt`
- [ ] PyInstaller spec file updated
- [ ] Resources included (icons, CSV)
- [ ] Version number updated in `gui.py`
- [ ] Build completes without errors
- [ ] Executable runs on clean Windows machine
- [ ] All UI elements visible
- [ ] Tag completion works (CSV loaded)
- [ ] Login/generation functional
- [ ] Logs created in correct location

### Version Management

**Current Version:** V4.5_2.5.11.26

**Location:** `gui.py:41`
```python
TITLE_NAME = "NAI Auto Generator V4.5_2.5.11.26"
```

**Version Format:** `V{major}.{minor}_{build}.{date}`
- Major: API version (V4, V4.5)
- Minor: Feature version
- Build: Build number
- Date: Release date (MM.DD format)

**Updating Version:**
1. Modify `TITLE_NAME` in `gui.py`
2. Update window title
3. Update README.md if needed
4. Commit with "ver update" message

---

## Important Files Reference

### Configuration Files

| File | Purpose | Format | Notes |
|------|---------|--------|-------|
| `requirements.txt` | Python dependencies | Text | Maintain version constraints |
| `consts.py` | Default parameters | Python | Central configuration |
| `.gitignore` | Git exclusions | Text | Excludes logs, builds, settings |

### Data Files

| File | Purpose | Size | Notes |
|------|---------|------|-------|
| `danbooru_tags_post_count.csv` | Tag completion database | ~450KB | Tag name, post count |
| `languages/*.json` | UI translations | ~30KB each | 4 languages supported |

### Resource Files

| File | Purpose | Format |
|------|---------|--------|
| `app_icon.ico` | Application icon | ICO |
| `icon.png` | UI icon resource | PNG |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview (Korean) |
| `credit.txt` | Attribution |
| `CLAUDE.md` | This file - AI assistant guide |

### Default Paths

```python
DEFAULT_PATH = {
    "path_results": "./results/",       # Generated images
    "path_settings": "./settings/",     # Saved settings
    "path_wildcards": "./wildcards/",   # Wildcard files
    "path_models": "./models/",         # ONNX tagger models
}
```

**Log Path:** `~/NAI-Auto-Generator/logs/`

### API Endpoints

**Base URL:** `https://image.novelai.net`

**Endpoints:**
- `POST /user/login` - Authentication
- `POST /ai/generate-image` - Image generation
- `GET /user/information` - User info & ANLAS
- `POST /user/logout` - Session termination

**Request Headers:**
```json
{
  "Authorization": "Bearer <token>",
  "Content-Type": "application/json"
}
```

### Supported Models

```python
NAI_MODELS = {
    "nai-diffusion-4-full": "NAI Diffusion V4 Full",
    "nai-diffusion-4-5-curated": "NAI Diffusion V4.5 Curated",
    "nai-diffusion-4-5-full": "NAI Diffusion V4.5 Full"  # Default
}
```

### Resolution Families

```python
RESOLUTION_FAMILIY = {
    0: ["Square (1024x1024)", "Portrait (832x1216)", "Landscape (1216x832)"],
    1: ["Square (1472x1472)", "Portrait (1024x1536)", "Landscape (1536x1024)"],
    2: ["Portrait (1088x1920)", "Landscape (1920x1088)"],
    3: ["Square (640x640)", "Portrait (512x768)", "Landscape (768x512)"],
    4: []  # Custom
}
```

---

## AI Assistant Guidelines

### When Working with This Codebase

**DO:**
- ✅ Read existing code before making changes
- ✅ Follow established naming conventions
- ✅ Add translations for all UI text
- ✅ Use QThread for long operations
- ✅ Add logging statements for debugging
- ✅ Update `consts.py` for new defaults
- ✅ Test with PyInstaller build
- ✅ Preserve existing code structure
- ✅ Use `resource_path()` for file access
- ✅ Handle exceptions gracefully

**DON'T:**
- ❌ Block the UI thread with long operations
- ❌ Hardcode file paths (use `resource_path()`)
- ❌ Skip internationalization (i18n)
- ❌ Ignore existing error handling patterns
- ❌ Create files without `create_folder_if_not_exists()`
- ❌ Modify API endpoints without testing
- ❌ Change version numbers without updating all locations
- ❌ Commit without descriptive messages
- ❌ Push to wrong branch
- ❌ Skip logging important operations

### Understanding User Intent

**Common Requests:**

| User Request | Likely Intent | Action |
|--------------|---------------|--------|
| "Add parameter X" | New generation option | Add to `consts.py`, `gui_init.py`, `gui.py`, API call |
| "Fix login issue" | Authentication problem | Check `nai_generator.py`, token handling, API changes |
| "Translation missing" | i18n incomplete | Add to all `languages/*.json` files |
| "UI freeze" | Blocking operation | Move to QThread worker |
| "Build fails" | PyInstaller issue | Check `distribute.bat`, resource paths |
| "Wildcard doesn't work" | File path problem | Verify `./wildcards/` structure |

### Code Reading Priority

**For Bug Fixes:**
1. `logger.py` - Check logs first
2. Affected module (e.g., `nai_generator.py` for API issues)
3. `gui.py` - Event handling
4. Related utility (e.g., `wildcard_applier.py`)

**For New Features:**
1. `consts.py` - Understand defaults
2. `gui_init.py` - See UI patterns
3. Similar existing feature - Follow pattern
4. `i18n_manager.py` - Plan translations

**For Understanding Flow:**
1. `gui.py` - Main window init
2. `nai_generator.py` - API client
3. Worker threads - Async operations
4. `gui_dialog.py` - User interactions

### Helpful Context

**This codebase is:**
- **Mature:** Extensive features, ~9K lines
- **GUI-heavy:** Most complexity in PyQt5
- **API-dependent:** Central reliance on Novel AI
- **Multi-language:** Always consider i18n
- **Windows-focused:** Primary target platform

**Key Dependencies:**
- Novel AI API availability
- PyQt5 for GUI
- ONNX models for tagging
- Wildcard files for dynamic prompts
- CSV database for tag completion

**Common Pain Points:**
- Token expiration (handled by NAISessionManager)
- Network timeouts (retry logic needed)
- PyInstaller resource paths (use `resource_path()`)
- Threading complexity (careful with signal/slot)
- Multi-language consistency (test all variants)

### Best Practices Summary

1. **Always use logging** - Critical for debugging
2. **Never block UI** - Use QThread for async
3. **Internationalize everything** - Support all languages
4. **Handle errors gracefully** - Try-except with user feedback
5. **Follow existing patterns** - Consistency matters
6. **Test PyInstaller builds** - Resource loading differs
7. **Preserve settings** - QSettings for persistence
8. **Document complex logic** - Help future maintainers
9. **Commit frequently** - Small, focused changes
10. **Respect user data** - Never delete without confirmation

---

## Quick Reference

### File Tree (Expanded)
```
NAI-Auto-V4/
├── gui.py                          # Main window (START HERE)
├── gui_init.py                     # Widget creation
├── gui_dialog.py                   # Dialogs
├── character_prompts_ui.py         # Character UI
├── nai_generator.py                # API client (CORE)
├── wildcard_applier.py             # Dynamic prompts
├── completer.py                    # Tag completion
├── danbooru_tagger.py              # ML tagging
├── i18n_manager.py                 # Translations
├── logger.py                       # Logging
├── consts.py                       # Configuration (IMPORTANT)
├── naiinfo_getter.py               # Metadata reader
├── stealth_pnginfo.py              # Hidden metadata
├── installer_zipper.py             # Distribution
├── requirements.txt                # Dependencies
├── distribute.bat                  # Build script
├── languages/
│   ├── ko.json                     # Korean
│   ├── en.json                     # English
│   ├── ja.json                     # Japanese
│   └── zh.json                     # Chinese
├── danbooru_tags_post_count.csv    # Tag database
├── app_icon.ico                    # App icon
├── icon.png                        # UI icon
├── README.md                       # Project info
├── credit.txt                      # Credits
└── CLAUDE.md                       # This file
```

### Key Functions & Classes

| Component | Location | Purpose |
|-----------|----------|---------|
| `NAIAutoGeneratorWindow` | gui.py:288 | Main application window |
| `NAIGenerator` | nai_generator.py:376 | API client |
| `NAISessionManager` | nai_generator.py:22 | Session lifecycle |
| `WildcardApplier` | wildcard_applier.py:9 | Prompt expansion |
| `I18nManager` | i18n_manager.py:8 | i18n singleton |
| `DanbooruTagger` | danbooru_tagger.py:46 | ML tagging |
| `CompletionTextEdit` | completer.py:63 | Tag completion |
| `resource_path()` | gui.py:47 | Resource loading |
| `tr()` | i18n_manager.py | Translation function |
| `get_logger()` | logger.py:7 | Logger instance |

### Constants Reference

```python
# From consts.py
DEFAULT_MODEL = "nai-diffusion-4-5-full"
DEFAULT_TAGCOMPLETION_PATH = "./danbooru_tags_post_count.csv"

DEFAULT_PARAMS = {
    "model": "nai-diffusion-4-5-full",
    "width": "1024",
    "height": "1024",
    "steps": "28",
    "sampler": "k_euler_ancestral",
    "scale": "5.0",
    "v4_model_preset": "Artistic",
    # ... (see consts.py for full list)
}

DEFAULT_PATH = {
    "path_results": "./results/",
    "path_settings": "./settings/",
    "path_wildcards": "./wildcards/",
    "path_models": "./models/",
}

COLOR = {
    'BUTTON_CUSTOM': '#559977',
    'BUTTON_AUTOGENERATE': '#D37493',
    'LABEL_SUCCESS': '#559977',
    'LABEL_FAILED': '#D37493',
}
```

### Signal/Slot Common Patterns

```python
# Define signal
my_signal = pyqtSignal(str, int)

# Connect to slot
self.my_signal.connect(self.my_handler)

# Emit signal
self.my_signal.emit("message", 42)

# Slot decorator (optional)
@pyqtSlot(str, int)
def my_handler(self, message, value):
    pass
```

### Translation Function

```python
from i18n_manager import tr

# In code
text = tr("key_name")

# In UI
button.setText(tr("button_text"))
label.setText(tr("label_text"))
```

---

## Appendix: External Resources

### Dependencies Documentation
- **PyQt5:** https://www.riverbankcomputing.com/static/Docs/PyQt5/
- **Pillow:** https://pillow.readthedocs.io/
- **requests:** https://requests.readthedocs.io/
- **ONNX Runtime:** https://onnxruntime.ai/docs/

### Related Projects
- **Original Fork:** https://github.com/DCP-arca/NAI-Auto-Generator
- **Stealth PNG Info:** https://github.com/neggles/sd-webui-stealth-pnginfo
- **WD14 Tagger:** https://github.com/pythongosssss/ComfyUI-WD14-Tagger
- **WD14 Models:** https://huggingface.co/SmilingWolf

### Novel AI Resources
- **Novel AI:** https://novelai.net
- **API Base:** https://image.novelai.net
- **Documentation:** (Internal API - no public docs)

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-14 | 1.0.0 | Initial comprehensive documentation |
| 2025-11-26 | 1.1.0 | Updated version to V4.5_2.5.11.26, updated branch info, recent commits |

---

## License & Credits

**Original Author:** DCP-arca (https://github.com/DCP-arca/NAI-Auto-Generator/)
**Current Maintainer:** sagawa8b
**License:** See original repository

**Referenced Projects:**
- sd-webui-stealth-pnginfo by neggles
- ComfyUI-WD14-Tagger by pythongosssss
- WD14 models by SmilingWolf & baqu2213

---

**End of CLAUDE.md**
