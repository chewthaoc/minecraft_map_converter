# 🌍 Minecraft World Converter

<div align="center">

![Version](https://img.shields.io/badge/version-0.2.0-blue)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-yellow)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub Stars](https://img.shields.io/github/stars/chewthaoc/minecraft_convert?style=social)
![GitHub Forks](https://img.shields.io/github/forks/chewthaoc/minecraft_convert?style=social)

</div>

**Language:** [English](#english) | [中文](README.zh-CN.md)

## English

A modern desktop tool built with Python and Tkinter that simplifies world
conversion between **Minecraft Java Edition** and **Bedrock Edition**. Powered
by the excellent [Amulet Core](https://github.com/Amulet-Team/Amulet-Core)
library.

<div align="center">

![Screenshot](https://img.shields.io/badge/UI-Modern%20%7C%20Intuitive-success)
![Downloads](https://img.shields.io/github/downloads/chewthaoc/minecraft_convert/total)

</div>

---

### ✨ Features

| Feature                 | Description                                                                 |
| :---------------------- | :-------------------------------------------------------------------------- |
| 🔄 **Bidirectional**    | Seamless **Java ↔ Bedrock** world conversion                                |
| 🔀 **Version Switch**   | Upgrade or downgrade within the same platform (e.g., Java 1.20 → Java 1.16) |
| 📦 **Batch Processing** | Import multiple worlds and convert them in one run                          |
| 🛠️ **Repair Mode**      | “Force Repair” re-saves chunks to fix corrupted data                        |
| 🎯 **Target Version**   | Choose exact versions (e.g., `1.20.1`, `1.19`)                              |
| 🖥️ **GUI**              | Clean GUI with real-time logs, no CLI required                              |

### 🚀 Quick Start

#### Windows (Executable)

1. Download the latest `mcconvert.exe` from Releases.
2. Double-click to launch.
3. **Select mode**:
   - **Single World**: convert one world folder.
   - **Batch Mode**: add multiple worlds and choose an output directory.
4. **Configure options**:
   - Select input/output paths.
   - Choose target version (default: Latest).
   - (Optional) enable **Force Repair** to rewrite chunk data.
5. Click **"Start Convert"**.

### 🛠️ Development

If you want to contribute or run from source:

#### Requirements

- Python 3.10 or 3.11 (recommended)
- Windows (recommended)

#### Setup

1. **Clone the repo**

   ```bash
   git clone https://github.com/chewthaoc/minecraft_convert.git
   cd minecraft_convert
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run**
   ```bash
   python main.py
   ```

### 📦 Build

This project uses `PyInstaller` to create a single-file executable.

```bash
pyinstaller --noconsole --onefile --name mcconvert --paths src --collect-all amulet main.py
```

> The output is located at `dist/mcconvert.exe`.

### ⚠️ Notes

- **Backup**: Conversion is destructive. **Always back up your worlds first.**
- **Version Support**: Target versions depend on Amulet updates. If a version is
  unsupported, the tool will pick the closest compatible option.
- **Runtime**: If you see DLL errors on another PC, install the
  [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170).

### 📝 License

MIT License. Built on top of Amulet-Core.

---

### 📊 Star History

<div align="center">

[![Star History Chart](https://api.star-history.com/svg?repos=chewthaoc/minecraft_convert&type=Date)](https://star-history.com/#chewthaoc/minecraft_convert&Date)

</div>

---

### 💖 Support

If this project helps you, please consider:

- ⭐ Starring the repo
- 🐛 Opening an Issue
- 🔀 Submitting a Pull Request
- 📢 Sharing it with others
