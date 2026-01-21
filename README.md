# Minecraft 存档转换工具

这是一个基于 Python + Tkinter 的桌面工具，用于在 Java 与 Bedrock 存档之间转换，同时支持同平台版本切换与修复。面向非技术用户，开箱即用。

## 功能
- 跨平台转换：Bedrock → Java、Java → Bedrock
- 同平台版本切换：Java → Java、Bedrock → Bedrock
- 强制修复（重新保存）
- 批量处理多个存档
- 目标版本选择
- 转换日志与错误提示

## 使用（已打包 EXE）
直接运行 dist/mcconvert.exe。

## 使用说明
1. 选择转换方向。
2. 选择输入存档（批量模式可添加多个）。
3. 选择输出目录：
   - 单个转换：输出目录需为空。
   - 批量转换：选择输出根目录，工具会自动创建同名子目录。
4. 选择目标版本（默认“最新”）。
5. 需要修复时勾选“强制修复(重新保存)”。
6. 点击“开始转换”。

## 常见说明
- 如果目标平台与源平台一致且未选择版本/修复，将直接复制存档。
- 目标版本来自 Amulet 内置版本列表；若指定版本不可用，将自动回退为最新版本。

## 开发与打包
### 运行（开发环境）
1. 安装 Python 3.11。
2. 安装依赖：`pip install -r requirements.txt`
3. 启动：`python main.py`

### 打包为单文件 EXE
执行：`pyinstaller --noconsole --onefile --name mcconvert --paths src --collect-all amulet main.py`

## 依赖与环境
- 转换依赖 Amulet，已随 EXE 打包。
- 如在其他电脑提示缺少系统运行库（如 VCRUNTIME），需先安装对应 Windows 运行库。
- 若 Amulet 版本不支持转换接口，会在日志中提示错误信息。
