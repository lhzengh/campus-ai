# ADR-0006：独立 Connector 协议、SDK 与运行边界

- 状态：接受
- 日期：2026-08-21

## 背景

Campus AI 需要支持不同学校的门户、认证方式和页面结构，并允许其他学校的用户或开发者提供适配实现。如果 Connector 直接导入 Core 的模型、任务处理器或数据库，新增学校就必须修改并重新发布 Core，第三方也难以独立开发和测试。

项目仍处于早期阶段。立即拆分多个 Git 仓库会增加协议联调、版本发布和跨仓库变更成本，但继续把抓取代码放入 Core 会形成更难清理的耦合。

## 决定

- 当前使用 Monorepo，Client、Core、Connector SDK 和官方 Connector 分目录管理；协议稳定和维护者边界明确后再决定是否拆仓。
- Client 仅调用 Client API，不能直接调用 Connector。Core 负责权限、审计、任务、数据库、AI、通知和设备同步。
- Core 仅通过版本化 HTTP/JSON Connector API 调用 Connector，不导入任何具体 Connector 实现。
- Connector 不访问 Core 数据库，不调用 AI 或通知服务，也不导入 Core 包；它只负责配置、认证、会话、采集、解析和统一输出。
- 独立 Python Connector SDK 定义 Manifest、配置校验、认证状态与挑战、同步请求、`CampusItemBatch` / `CampusItem`、统一错误及 FastAPI 服务包装器。
- 每个 Connector 具有独立包、依赖、测试、版本和 Docker 镜像。官方 Connector 可以与 Core 同仓库，但必须能在未安装 Core 的环境独立运行。
- Core 通过运行时端点注册表定位 Connector，并校验注册 ID、Manifest ID、Connector 版本和协议版本。端点和共享认证 Token 不进入客户端或源代码。
- Connector Manifest 使用 JSON Schema 描述配置；Secret 字段由扩展属性标记。Core 负责 Secret 的安全保存和挑战转发，但不理解学校专用字段。
- 同步使用不透明游标和统一 `CampusItemBatch` 输出，具体事实边界与字段语义由 CampusItem Contract v1 定义。标准错误决定 Core 是重试、退避、暂停来源还是请求用户重新认证。
- SDK 提供可复用兼容性测试。协议契约保存在 `contracts/connector-api/`，协议发生破坏性变化时提升主版本。

## 后果

新增学校通常只需实现和发布新的 Connector，不需要修改 Core 或 Flutter。某个 Connector 的依赖、浏览器版本和运行故障可以独立隔离，未来也可使用其他语言实现协议。

代价是本地部署会多出服务间 HTTP、端点注册、协议版本和容器健康检查。认证信息跨进程传递必须使用受保护的内部网络、共享服务凭据和日志脱敏；生产部署仍需 TLS 或等效的可信网络边界。

Core 内部继续采用 ADR-0001 的模块化单体；被取代的仅是“来源适配器位于 Core、Playwright 作为 Core Browser Worker”的部分。
