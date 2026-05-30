# Avalon Miner Scanner

Avalon Miner Scanner 是一个基于 Python/Tkinter 的 Avalon 矿机局域网扫描与运维工具。它可以扫描指定 IP 段内开放 `4028` 端口的矿机，读取型号、固件版本、DNA、MAC、运行时间、算力、HASH 板 SN、CPU 等信息，并提供 LED 控制、日志查看、静态 IP 批量配置、CSV 导出和 Windows EXE 打包产物。

## 快速运行

源码运行：

```bash
python main.py
```

Windows 打包产物：

```text
dist/Avalon矿机扫描工具V1.0.5.exe
```

项目主要依赖 Python 标准库，包括 `tkinter`、`socket`、`threading`、`urllib`、`csv/json/re` 等。当前代码没有单独的依赖清单文件。

## 主要功能

- 扫描指定 IP 段内的 Avalon 矿机。
- 展示矿机 IP、型号、版本、DNA、MAC、运行时间、算力、HASH 板 SN 和 CPU 信息。
- 打开矿机 Web 管理页面，支持部分设备的自动登录/认证跳转。
- 控制单台或批量矿机 LED 点灯、关灯。
- 查看矿机详细日志，并用图形化方式展示芯片温度、电压、频率等运行状态。
- 监听矿机 UDP IP 上报，并批量下发静态 IP 配置。
- 导出扫描结果 CSV 和完整矿机响应日志。
- 使用 PyInstaller 生成 Windows 可执行文件。

## 文件树

```text
.
├── README.md
├── ConnectionManager.py
├── gui.py
├── ip_manager.py
├── ip_report.py
├── ip_segments.json
├── log_viewer.py
├── main.py
├── miner_operations.py
├── network_scanner.py
├── utils.py
├── dist/
│   ├── Avalon矿机扫描工具V1.0.5.exe
│   └── imag/
│       └── avalon.ico
├── imag/
    └── avalon.ico

```

## 源码说明

### `main.py`

程序入口。创建 Tkinter 根窗口并启动 `MinerScannerGUI`。

### `gui.py`

主界面模块。负责窗口布局、扫描按钮、结果表格、进度条、右键菜单、复制、删除、清空、CSV 导出、详细日志导出、LED 批量控制、打开日志可视化窗口等交互逻辑。

主界面表格字段包括：

- IP
- MODEL
- VERSION
- DNA
- MAC
- TIME
- Elapsed
- GHSspd
- HASH0 到 HASH3
- CPU

### `network_scanner.py`

网络扫描模块。根据启用的 IP 段生成目标 IP，使用线程池并发连接矿机 `4028` 端口，发送 `version`、`estats`、`ascset|0,hash-sn-read,*` 等命令，解析并回传扫描结果。

### `miner_operations.py`

矿机操作模块。提供：

- LED 点灯/关灯。
- LED 状态查询。
- 单台矿机信息刷新。
- 获取算力、运行时间、CPU、HASH 板 SN。
- 打开矿机 Web 页面。
- 为部分设备生成自动登录 HTML 或认证 URL。

### `ConnectionManager.py`

连接池管理模块。维护 TCP socket 连接池、连接健康分、网络评分、自适应超时、连接清理等逻辑。当前扫描主流程里保留了连接管理对象，但多数矿机命令仍是按需创建 socket。

### `ip_manager.py`

IP 段管理模块。负责加载、保存、校验 `ip_segments.json` 中的 IP 段配置，支持 `IP段#标签` 格式。

示例格式：

```text
192.168.1.1-255
10.100.106.1-10#机房A
```

### `ip_report.py`

批量静态 IP 配置模块。提供独立窗口用于：

- 监听 UDP `10002` 端口的矿机 IP 上报。
- 解析上报数据中的 IP、设备类型、MAC。
- 分配目标 IP。
- 发送 `ascset|0,ip,s,...` 静态 IP 配置命令。
- 导出 IP 上报记录 CSV。

### `log_viewer.py`

矿机日志可视化模块。连接矿机 `4028` 端口读取 `stats` 数据，并将芯片温度、电压、MW、算力、CRC、风扇、电源等信息用图形界面展示。

### `utils.py`

通用工具模块。包含：

- IP 段格式校验。
- IP 段文本解析。
- 矿机响应解析。
- MAC 地址标准化。
- 运行时间格式化。

## 配置和数据文件

### `ip_segments.json`

保存用户配置的扫描 IP 段。当前文件中包含若干内网网段和标签，用于主界面 IP 段列表。

### `miner_details/`

历史矿机详细日志导出目录。每个 `.txt` 文件通常包含：

- IP
- 型号
- 固件版本
- DNA
- HASH 板 SN
- 矿机时间和导出时间
- `VERSION` 原始响应
- `HASH` 原始响应
- `LOG/STATS` 原始响应

这些文件包含真实设备标识和运行状态，分享项目时建议移除或脱敏。

### `canaan_avalon_miner_*.html`

自动登录矿机 Web 管理页面时生成的本地 HTML 文件。文件内包含提交到矿机管理页面的表单字段，属于运行产物。

## 资源和构建产物

### `imag/avalon.ico`

主程序窗口和打包 EXE 使用的图标资源。

### `dist/`

PyInstaller 输出目录。当前包含：

- `Avalon矿机扫描工具V1.0.5.exe`：Windows 可执行程序。
- `imag/avalon.ico`：随发布目录保留的图标。

