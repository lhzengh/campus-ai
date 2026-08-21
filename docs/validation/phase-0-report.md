# 阶段 0 技术验证报告

> 状态：执行中（基础设施、Connector 平台与 Linux 客户端已通过）
> 开始日期：2026-08-19
> 最近验证：2026-08-21
> 验证环境：Arch Linux x86_64、Intel i5-10210U、15 GiB 内存

## 1. 目标与门槛

| 验证项 | 通过标准 | 当前状态 |
| --- | --- | --- |
| Docker 多服务 | 一条命令启动；数据跨容器重建保留；任务可恢复 | 通过：空卷迁移、健康检查、任务消费、去重、容器重建持久化及独立 Connector 通信均通过 |
| 静态来源 | 30 条真实消息字段成功率不低于 98%，重复率低于 2% | 接口与固定样本通过；等待真实网址 |
| 认证门户 | 用户辅助登录、加密会话、失效告警，不绕过验证码 | 独立浏览器 Connector、加密存储单测和 Playwright/Chromium 容器运行通过；等待真实入口 |
| 公众号 | 至少一种合规且可持续路径，失败时有手动分享降级 | 等待公众号名单 |
| 云端 AI | Schema 成功率 ≥99%，重要消息召回率 ≥95%，截止时间准确率 ≥95% | Mock API 通过；等待 API 配置与 50 条脱敏样本 |
| Android 推送 | 送达率 ≥95%，95% 在 60 秒内到达，重复率 0 | FCM/UnifiedPush发送器完成；等待真机、GMS模拟器及服务配置 |
| Flutter 多端 | Linux、Android、Windows 构建成功；离线状态可同步 | Linux Debug 构建通过；分析/测试通过；Android 缺 SDK，Windows 等待 GitHub Runner |

## 2. 已完成实现

- Compose 定义 PostgreSQL、Core API、Worker、Scheduler、静态 Connector 和可选浏览器 Connector。
- API、Worker、Scheduler 共用 Python 3.13 Core 镜像；静态抓取与 Playwright 分别进入独立 Connector 镜像。
- 建立版本化 HTTP/JSON Connector API、独立 Python SDK、Manifest、配置 Schema、认证挑战、统一消息/批次和错误模型。
- Core 通过运行时 Connector ID→端点注册表通信，不导入具体 Connector；Connector 不安装 Core 或访问 Core 数据库。
- PostgreSQL 任务表支持去重键、有限重试、指数退避和陈旧锁恢复。
- Alembic 初始迁移包含来源、消息、分析、任务和通知送达记录。
- 静态 HTTP Connector 支持 CSS 选择器、URL 规范化、显式域名白名单、安全重定向、限速、时区解析和增量游标。
- Playwright Connector 独立保存 Fernet 加密会话，Core 不接触 Cookie，验证码仅允许用户人工处理。
- OpenAI 兼容 API 使用严格 JSON Schema，并以 Pydantic 校验输出。
- FCM 与 UnifiedPush 具有统一通知接口；数据库层按渠道、设备和事件去重。
- 提供真实来源、AI 数据集和推送批量探测脚本。
- 创建 Flutter 3.47 三端工程，采用 Material 3、Riverpod、go_router 与 Drift/SQLite。
- 客户端支持消息同步、本地缓存、已读状态、响应式导航、原文详情、FCM Token 诊断，以及通过 Core 完成 Connector 发现、Schema 动态配置、认证挑战和手动同步任务轮询。
- 客户端以英文作为完整回退语言，提供可选中文展示；协议字段、错误码、配置键和 Connector ID 不参与本地化。
- FCM 接收日志和指标脚本可计算真机送达率、重复率与 P95 延迟。

## 3. 自动化结果

2026-08-21 最新本地执行：

```text
pytest: 37 passed（SDK、两个 Connector 与 Core）
aggregate Python coverage: 73%
flutter analyze: No issues found
flutter test: 9 passed
flutter build linux --debug: succeeded
Alembic 空数据库及带旧消息的 SQLite `0002` 数据库迁移: upgraded to 0003
Compose: 空 PostgreSQL 18 数据卷启动成功，api/postgres healthy
Connector: Core 经内部 Bearer Token 发现静态 Connector Manifest；未启动的可选 Connector 返回 unavailable，不影响健康 Connector
Source API: 通过 Connector Schema 校验并持久化一个仅使用保留示例域名的临时来源
Source UI/API: Flutter Widget 测试完成 Schema 表单来源创建；隔离 Compose 使用同一配置结构经 Core、Worker 与静态 Connector 完成同步，标准消息可由 Client API 读取
Worker: fetch_all 任务 1 次成功；相同 dedupe_key 返回同一任务
Persistence: 容器全部重建后任务仍存在
Playwright: 独立 browser Connector 镜像内 Chromium 启动并渲染页面成功
Isolation: Core 镜像确认不包含 Playwright
```

覆盖场景：

- 任务去重、完成、重试终止与陈旧锁恢复。
- API契约和OpenAPI路径生成。
- 静态页面发现、链接去重、正文解析与带时区日期。
- 云端AI结构化响应校验。
- UnifiedPush请求结构和通知事件去重。
- 门户会话密文不包含原始Cookie。
- Flutter 后端 API 契约解析、Drift 离线缓存与已读状态保留。
- Flutter 消息列表、详情路由和 Material 3 关键界面。
- Flutter Connector 发现、动态表单默认值/Secret 隔离、来源创建、通用认证挑战、任务状态和英中展示层。
- PostgreSQL 18 数据卷挂载、一次性迁移依赖和服务启动次序。
- API 入队、数据库持久队列、Worker 消费和任务去重的真实容器链路。
- Playwright 浏览器镜像不只构建成功，Chromium 也已实际启动。
- Connector SDK 服务包装器、Manifest 身份/主协议版本检查、独立 Token 和第三方兼容性测试。
- 单个 Connector 不可用时的发现列表故障隔离。
- 静态 Connector 对越界链接和跨域重定向的阻断。
- 隔离 Compose 首次暴露并修复 Worker 环境覆盖导致 Connector 注册表丢失的问题；修复后两次同步均成功，数据库只保留一条幂等消息，验证容器、网络和临时卷已删除。

## 4. 尚需外部输入

- 仍需对一个通过私有运行配置提供的认证门户执行用户在场登录、页面结构、访问边界和会话寿命实测；真实网址和账号信息不写入仓库。
- 1–3 个公众号名称及允许使用的获取方式。
- 50 条脱敏真实消息及人工重要性、截止时间标注。
- OpenAI 兼容 API 的 Base URL、模型名和仅在本地配置的密钥。
- 一台国内 Android 真机、一个 GMS 模拟器、Firebase 项目/服务账号和 UnifiedPush 端点。
- GitHub 私有仓库已建立；最新分支 CI 仍需在推送后确认。

## 5. 剩余环境条件

Docker 29.7.2、Compose 5.4.0、ADB、JDK 17、clang、CMake、Ninja、pkg-config 和 GTK3 均已安装。当前自动化会话可通过 `newgrp docker -c '<命令>'` 验证；用户重新登录后可直接运行 Docker。Docker 组权限接近 root，只应授予可信用户。

本机 `flutter doctor -v` 已确认 Flutter 3.47.0、Dart 3.13.0 和 Linux 工具链可用，但找不到 Android SDK。还需通过 Android Studio 安装 SDK、当前 Platform、Build Tools 和 Command-line Tools，并在真实终端运行 `adb devices -l`。当前受限自动化会话不能创建 `~/.android`，这不是项目代码故障。

FCM 真机验收仍需要 Firebase 配置、服务账号以及 GMS 真机或模拟器；Windows 构建仍需要 Windows Runner。逐步命令见 `docs/validation/fcm-device-test.md`。
