# FCM 真机验证手册

> 状态：测试工具已实现；ADB/JDK 已安装，等待 Android SDK、Firebase 项目配置和真机
> 更新日期：2026-08-21

## 1. 当前边界

Docker 不是 FCM 真机测试的硬性前提。Flutter 客户端负责取得设备 Token 和记录实际收件时间，Python 探测器可直接从本地虚拟环境调用 FCM HTTP v1 API。Docker 只负责后端长期部署与完整系统联调。

仓库已经具备：

- Android 客户端可选 FCM 初始化、权限请求、Token 展示与复制。
- 前台、后台及点击通知启动时的结构化接收日志。
- 使用服务账号向单个 Token 批量发送唯一事件的工具。
- 计算送达率、重复率和 P95 延迟的日志分析工具。

尚缺：Android SDK、Firebase 项目、Android 应用配置、服务账号和已连接的 GMS 真机或模拟器。ADB 1.0.41 与 JDK 17 已安装；`flutter doctor -v` 已确认当前阻塞点是找不到 Android SDK。

## 2. 本机系统准备

Arch Linux 系统包已安装。若在另一台机器复现，可由设备所有者在真实终端执行：

```bash
sudo pacman -S --needed docker docker-compose android-tools jdk17-openjdk clang cmake gtk3
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

加入 `docker` 组后需要重新登录。当前机器可在真实终端验证：

```bash
docker version
docker compose version
adb version
java -version
```

还需通过 Android Studio 安装 Android SDK、当前稳定版 Platform、Build Tools 和 Command-line Tools，然后让 Flutter 识别 SDK：

```bash
./.tooling/flutter/bin/flutter config --android-sdk /你的/Android/Sdk
./.tooling/flutter/bin/flutter doctor -v
```

## 3. Firebase 准备

1. 在 Firebase 控制台创建或选择项目。
2. 注册 Android 应用，包名必须是 `ai.campus.campus_ai_client`。
3. 将 `frontend/firebase-config.example.json` 复制为被 Git 忽略的 `frontend/firebase-config.json`，填写 API Key、App ID、Project ID 和 Messaging Sender ID。
4. 在 Firebase 项目设置中创建仅用于本次验证的服务账号私钥，保存为 `.secrets/firebase-service-account.json`。该文件是真实密钥，不得提交、截图或粘贴到 Markdown。

客户端使用显式 `FirebaseOptions`，因此无需把 `google-services.json` 提交到仓库。

## 4. 取得设备 Token

在真机开启开发者选项和 USB 调试，确认设备已经授权：

```bash
adb devices -l
cd frontend
../.tooling/flutter/bin/flutter run -d <设备ID> \
  --dart-define-from-file=firebase-config.json
```

进入“设置与诊断 → Android 推送”，状态应显示“FCM 已就绪”。复制设备 Token。若真机没有可用的 Google Play 服务，应改用 GMS 模拟器验证 FCM，并把国内真机留给 UnifiedPush 验证。

## 5. 批量发送并采集日志

先清空日志，再持续采集：

```bash
adb logcat -c
adb logcat > fcm-device.log
```

另开终端，从仓库根目录发送 20 条探测通知：

```bash
.venv/bin/python spikes/push_probe.py --count 20 --interval 1 fcm '<设备Token>' \
  --project-id '<Firebase Project ID>' \
  --credentials .secrets/firebase-service-account.json
```

记录发送器输出中的 `run_id`。测试应分别覆盖应用前台、后台、被系统终止、设备重启和断网恢复；每种状态单独采集日志和发送 20 条。

停止 `adb logcat` 后计算指标：

```bash
.venv/bin/python spikes/fcm_log_evaluate.py fcm-device.log \
  --expected 20 --run-id '<run_id>'
```

通过门槛：送达率不低于 95%，P95 延迟不超过 60 秒，重复数为 0。FCM HTTP v1 返回 accepted 只表示服务端接受请求，不能代替真机接收日志。

## 6. 安全与清理

- 服务账号只存放在 `.secrets/`，测试结束后可在 Firebase 控制台吊销。
- 设备 Token 虽不是账号密码，也不应写入提交记录或公开日志。
- `frontend/firebase-config.json` 和 `fcm-*.log` 已加入 `.gitignore`。
- 不得把 AI API Key、门户 Cookie 与 Firebase 服务账号混用或传给客户端。
