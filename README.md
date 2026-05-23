<div align="center">

# 🐾 猫娘视频下载器

**NekoMeko Video Downloader**

一个可爱的 yt-dlp 图形化前端，支持多平台视频下载

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-FF69B4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-FFA500?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

[![Release](https://img.shields.io/github/v/release/linyaocrush/Nekomeko-Video-Downloader?style=for-the-badge&color=FF69B4)](https://github.com/linyaocrush/Nekomeko-Video-Downloader/releases/latest)

</div>

---

## ✨ 功能特性

<table>
<tr>
<td width="50%">

### 🎬 下载模式
- **最佳喵 (Auto)** — 自动选择最佳画质
- **手动挑选 (Manual)** — 自由选择视频/音频流
- **直播蹲守 (Live)** — 支持直播录制
- **只要声音 (MP3)** — 仅提取音频
- **只要小纸条 (字幕)** — 单独下载字幕
- **只抓聊天室 (Chat)** — 抓取直播弹幕

</td>
<td width="50%">

### 🛠️ 高级功能
- **断点续传** — 中断后自动恢复下载
- **批量下载** — 一次性添加多个链接
- **取消任务 / 取消队列** — 随时停止，子进程同步终止
- **队列持久化** — 退出后重启自动恢复未完成任务
- **SponsorBlock** — 自动跳过广告片段
- **自定义命名** — 灵活的文件名模板
- **代理支持** — HTTP 代理配置
- **Cookie 授权** — 浏览器 Cookie 提取
- **折叠式设置** — 高级选项默认收起，界面清爽

</td>
</tr>
<tr>
<td>

### 🎨 主题系统
- Material Design 3 色彩体系
- 内置 3 套主题预设（猫娘粉 / 深邃夜 / 清爽蓝）
- 可视化调色板自定义
- 支持浅色 / 深色模式

</td>
<td>

### 🐱 猫娘心情
- 实时心情反馈系统
- 根据下载状态变化
- 空闲、开心、兴奋、困倦…
- 独特的互动体验

</td>
</tr>
</table>

---

## 🚀 快速开始

### 下载打包版（推荐）

前往 [Releases](https://github.com/linyaocrush/Nekomeko-Video-Downloader/releases/latest) 下载：

| 版本 | 说明 |
|------|------|
| `*-single.exe` | 单文件版，双击即用 |
| `*-portable.zip` | 绿色免安装版，解压后运行 `Nekomeko.exe` |

> 两个版本都需要系统已安装 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 和 [ffmpeg](https://ffmpeg.org/) 并加入 PATH

#### 安装 yt-dlp 与 ffmpeg

```bash
# yt-dlp — 视频下载核心
# 方式一：pip 安装
pip install yt-dlp
# 方式二：下载 exe 放入 PATH
# https://github.com/yt-dlp/yt-dlp/releases

# ffmpeg — 音视频合并（可选但推荐）
# 下载地址：https://github.com/BtbN/FFmpeg-Builds/releases
# 下载 ffmpeg-master-latest-win64-gpl.zip，解压后将 bin/ 目录加入系统 PATH

# 💡 也可以将 yt-dlp.exe / ffmpeg.exe 直接放在程序根目录，无需加入 PATH
```

### 从源码运行

#### 环境要求

- **Python** 3.12 或更高版本
- **yt-dlp** （视频下载核心）
- **ffmpeg** （音视频合并，可选）

#### 安装与运行

```bash
# 1. 克隆仓库
git clone https://github.com/linyaocrush/Nekomeko-Video-Downloader.git
cd Nekomeko-Video-Downloader

# 2. 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\pip install -r requirements.txt

# 3. 双击运行
run.bat
```

> 💡 也可以直接双击 `run.bat`，会自动使用项目内置的虚拟环境启动

---

## 📁 项目结构

```
├── run.bat                      # ⚡ 一键启动 (pythonw -m neko.main)
├── requirements.txt             # 📦 Python 依赖
│
├── neko/                        # 🐱 主包
│   ├── main.py                  #   启动入口
│   │
│   ├── core/                    #   ⚙️ 核心模块
│   │   ├── constants.py         #     字体、主题模板、路径常量
│   │   ├── utils.py             #     装饰器、通知工具函数
│   │   ├── models.py            #     Pydantic 数据模型
│   │   ├── cache.py             #     启动缓存管理
│   │   ├── theme.py             #     主题管理器
│   │   └── process.py           #     统一 subprocess 封装
│   │
│   ├── data/                    #   💾 数据层
│   │   ├── database.py          #     SQLite 数据库操作
│   │   └── mood.py              #     猫娘心情系统
│   │
│   └── ui/                      #   🖼️ 界面层
│       ├── loading.py           #     启动加载屏
│       ├── main_window.py       #     主窗口 (布局 + 生命周期)
│       ├── stats.py             #     统计面板
│       ├── resume.py            #     续传管理窗口
│       ├── dialogs.py           #     7 个对话框合并
│       │
│       └── mixins/              #     主窗口业务逻辑拆分
│           ├── download.py      #       yt-dlp 下载引擎
│           ├── queue.py         #       下载队列 + 持久化恢复
│           ├── resume.py        #       续传会话追踪
│           ├── scheduler.py     #       非阻塞任务调度 + 取消
│           └── ui_helpers.py    #       UI 状态 / 启动维护
│
├── data/                        # 📂 运行时数据（自动创建）
│   ├── config.json              #     用户配置
│   ├── neko_history.db          #     下载历史
│   ├── themes/                  #     主题文件
│   └── cookies/                 #     Cookie 文件
│
└── cache/                       # ⚡ 启动缓存（自动创建）
```

---

## 🎮 使用指南

### 基本下载

1. 在输入框粘贴视频链接
2. 点击 **🐾 先闻一闻** 预览视频信息
3. 点击 **📥 放进篮子** 加入队列，或 **⚡ 立即抓取** 直接下载
4. 点击 **🚀 叼回窝里** 开始处理队列

### 手动选画质

1. 将模式切换为 **手动挑选 (Manual)**
2. 粘贴链接并点击预览
3. 从下拉框选择想要的视频流和音频流
4. 开始下载

### 批量下载

1. 点击 **📚 批量喂食**
2. 在弹出窗口中每行粘贴一个链接
3. 点击 **✅ 全部吞掉**

### 取消下载

- 右键队列中的任务 → **❌ 取消此任务**
- 点击底部 **🛑 取消队列** 按钮取消所有任务
- 子进程会被自动终止，不会残留

### 队列恢复

- 正常退出时队列自动保存到数据库
- 重新打开程序时，如有未完成任务会弹窗提示恢复
- 已完成的任务不会重复显示

---

## ⚙️ 配置说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| 下载目录 | 文件保存位置 | `~/Videos` |
| 代理 | HTTP 代理地址 | 关闭 |
| Cookie | 浏览器 Cookie | 无 |
| 并发数 | 同时下载任务数 | 2 |
| 字幕嵌入 | 下载后自动嵌入字幕 | 关闭 |
| 列表模式 | 下载整个播放列表 | 关闭 |

---

## 📋 依赖项

| 包名 | 用途 |
|------|------|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 现代化 GUI 框架 |
| [pydantic](https://docs.pydantic.dev/) | 数据验证与模型 |
| [Pillow](https://python-pillow.org/) | 图像处理（缩略图） |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 视频下载核心引擎 |
| [ffmpeg](https://ffmpeg.org/) | 音视频转码合并 |

---

## 📜 许可证

本项目基于 **MIT License** 开源，仅供个人学习交流使用。

<div align="center">

**请勿将本工具用于商业用途或侵犯版权的行为**

<br/>

<img src="https://img.shields.io/badge/made_with_❤️_by-linyaocrush-FF69B4?style=for-the-badge" />

</div>
