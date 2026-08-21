# ADR-0001：模块化单体与容器边界

- 状态：部分被 ADR-0006 取代
- 日期：2026-08-19

## 背景

项目由单人维护，初期数据量有限，但 API、定时调度、长时间采集任务和数据库需要独立生命周期。

## 决定

服务端采用 Python 模块化单体。API、Worker和Scheduler共用同一代码与镜像，以不同命令运行；PostgreSQL独立容器；Playwright最初使用可选Browser Worker构建目标。数据库迁移由一次性Migrate服务完成，API、Worker、Scheduler和Browser Worker仅在迁移成功后启动。Docker Compose统一管理服务、网络和Volume。

## 后果

保持一套后端代码和较低部署成本，同时可以独立重启故障进程。暂不采用Kubernetes、Redis和Celery；任务规模或并发证明确有需要后再评估。

ADR-0006 保留 Core 内部的模块化单体决定，但将来源适配和 Playwright 从 Core/Browser Worker 中移出，改为通过标准协议运行的独立 Connector 服务。
