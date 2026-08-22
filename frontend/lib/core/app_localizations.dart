// Provides English-first UI strings with optional Simplified Chinese support.

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

/// Lightweight app strings with English as the compatibility fallback.
class CampusStrings {
  const CampusStrings(this.locale);

  final Locale locale;

  bool get _zh => locale.languageCode == 'zh';

  static CampusStrings of(BuildContext context) =>
      Localizations.of<CampusStrings>(context, CampusStrings) ??
      const CampusStrings(Locale('en'));

  static const delegate = _CampusStringsDelegate();
  static const supportedLocales = [Locale('en'), Locale('zh')];

  String get inbox => _zh ? '消息' : 'Inbox';
  String get sources => _zh ? '来源' : 'Sources';
  String get settings => _zh ? '设置' : 'Settings';
  String get inboxTitle => _zh ? '校园消息' : 'Campus inbox';
  String get sourcesTitle => _zh ? '信息来源' : 'Sources';
  String get settingsTitle => _zh ? '设置与诊断' : 'Settings and diagnostics';
  String get retry => _zh ? '重试' : 'Retry';
  String get refresh => _zh ? '刷新' : 'Refresh';
  String get cancel => _zh ? '取消' : 'Cancel';
  String get save => _zh ? '保存' : 'Save';
  String get continueLabel => _zh ? '继续' : 'Continue';
  String get backToInbox => _zh ? '返回消息列表' : 'Back to inbox';
  String get pendingAi => _zh ? 'AI 分析待同步' : 'AI analysis pending';
  String get originalContent => _zh ? '原文信息' : 'Original content';
  String get openOriginal => _zh ? '打开原文' : 'Open original';
  String messageReadFailed(Object error) =>
      _zh ? '读取消息失败：$error' : 'Could not read message: $error';
  String get messageMissing =>
      _zh ? '消息不存在或尚未同步' : 'The message is missing or not yet synced.';
  String inboxSyncFailed(Object error) =>
      _zh ? '同步失败：$error' : 'Sync failed: $error';
  String get emptyInbox => _zh ? '暂无校园消息' : 'No campus messages yet';
  String get emptyInboxHint => _zh
      ? '下拉刷新，或先启动服务端并配置消息来源。'
      : 'Pull to refresh, or start Core and configure a source.';
  String localInboxFailed(Object error) =>
      _zh ? '无法读取本地消息：$error' : 'Could not read the local inbox: $error';

  String get server => _zh ? '服务端' : 'Server';
  String get apiAddress => _zh ? 'API 地址' : 'API address';
  String get androidPush => _zh ? 'Android 推送' : 'Android push';
  String get checkingFcm => _zh ? '检查 FCM 配置…' : 'Checking FCM configuration…';
  String get fcmCheckFailed => _zh ? 'FCM 检查失败' : 'FCM check failed';
  String get deviceToken => _zh ? '设备 Token' : 'Device token';
  String get copyToken => _zh ? '复制 Token' : 'Copy token';
  String get tokenCopied => _zh ? 'Token 已复制' : 'Token copied';
  String get privacyBoundary => _zh ? '隐私边界' : 'Privacy boundary';
  String get cloudAi => _zh ? '云端 AI' : 'Cloud AI';
  String get cloudAiDetail => _zh
      ? '由服务端通过 OpenAI 兼容 API 调用；客户端不保存模型密钥。'
      : 'Core uses an OpenAI-compatible API; the client never stores model keys.';
  String get mcpDetail => _zh
      ? '当前不承担模型推理，仅为未来受限工具接入预留。'
      : 'MCP does not perform inference and is reserved for future restricted tools.';

  String pushTitle(String kind) => switch (kind) {
    'unsupported_platform' =>
      _zh ? '当前平台不使用 FCM' : 'FCM is not used on this platform',
    'disabled' => _zh ? 'FCM 未启用' : 'FCM is disabled',
    'incomplete' => _zh ? 'FCM 配置不完整' : 'FCM configuration is incomplete',
    'missing_token' => _zh ? '未取得 FCM Token' : 'No FCM token received',
    'ready' => _zh ? 'FCM 已就绪' : 'FCM is ready',
    'failed' => _zh ? 'FCM 初始化失败' : 'FCM initialization failed',
    _ => kind,
  };
  String pushDetail(String kind, String detail) => switch (kind) {
    'unsupported_platform' =>
      _zh ? 'Linux 与 Windows 保留应用内同步；FCM 仅在 Android 启用。' : 'Linux and Windows use in-app sync; FCM is enabled only on Android.',
    'disabled' => _zh ? '使用 ENABLE_FCM 和四项 Firebase Dart Define 启动应用后再检查。' : 'Start with ENABLE_FCM and the four Firebase Dart defines, then check again.',
    'incomplete' =>
      _zh
          ? '缺少 API Key、App ID、Project ID 或 Messaging Sender ID。'
          : 'API Key, App ID, Project ID, or Messaging Sender ID is missing.',
    'missing_token' ||
    'ready' => _zh ? '通知权限：$detail' : 'Notification permission: $detail',
    _ => detail,
  };

  String get addSource => _zh ? '添加来源' : 'Add source';
  String get chooseConnector => _zh ? '选择 Connector' : 'Choose a Connector';
  String get availableConnectors =>
      _zh ? '可用 Connector' : 'Available Connectors';
  String get noSources => _zh ? '尚未配置来源' : 'No sources configured';
  String get noSourcesHint => _zh
      ? '添加 Connector 来源后，Core 才能定时收集消息。'
      : 'Add a Connector source so Core can collect messages on schedule.';
  String get noConnectors =>
      _zh ? '没有已注册的 Connector' : 'No Connectors registered';
  String get connectorUnavailable => _zh ? '不可用' : 'Unavailable';
  String get connectorIncompatible => _zh ? '协议不兼容' : 'Incompatible';
  String get requiresBrowser => _zh ? '需要浏览器' : 'Requires browser';
  String get configure => _zh ? '配置' : 'Configure';
  String get sourceName => _zh ? '来源名称' : 'Source name';
  String get sourceNameHint =>
      _zh ? '例如：学院通知' : 'For example: Department notices';
  String get connectorConfiguration =>
      _zh ? 'Connector 配置' : 'Connector configuration';
  String get createSource => _zh ? '创建来源' : 'Create source';
  String get sourceCreated => _zh ? '来源已创建' : 'Source created';
  String get sourceSaved => _zh ? '来源已保存' : 'Source saved';
  String get editSource => _zh ? '编辑来源' : 'Edit source';
  String get sourceEnabled => _zh ? '启用来源' : 'Source enabled';
  String get sourceEnabledHint => _zh
      ? '停用后仍保留配置和历史消息。'
      : 'Disabled sources keep their configuration and message history.';
  String get collectionSchedule => _zh ? '采集计划' : 'Collection schedule';
  String get scheduleMode => _zh ? '计划模式' : 'Schedule mode';
  String get manualOnly => _zh ? '仅手动' : 'Manual only';
  String get daily => _zh ? '每天' : 'Daily';
  String get dailyTime => _zh ? '每日时间' : 'Daily time';
  String get timezone => _zh ? '时区' : 'Timezone';
  String get timezoneHint =>
      _zh ? 'IANA 名称，例如 Asia/Shanghai' : 'IANA name, for example Asia/Shanghai';
  String get showArchived => _zh ? '显示已归档' : 'Show archived';
  String get archived => _zh ? '已归档' : 'Archived';
  String get enabled => _zh ? '已启用' : 'Enabled';
  String get disabled => _zh ? '已停用' : 'Disabled';
  String get connectionCheck => _zh ? '检查连接' : 'Check connection';
  String get connectionReady =>
      _zh ? 'Connector 与配置均可用' : 'Connector and configuration are ready';
  String get preview => _zh ? '预览' : 'Preview';
  String get previewTitle => _zh ? '来源预览' : 'Source preview';
  String get noPreviewItems => _zh ? '未返回预览消息' : 'No preview items returned';
  String get archive => _zh ? '归档' : 'Archive';
  String get restore => _zh ? '恢复' : 'Restore';
  String get archiveSource => _zh ? '归档来源？' : 'Archive source?';
  String get archiveSourceHint => _zh
      ? '来源将被停用并隐藏，历史消息会保留。'
      : 'The source will be disabled and hidden. Message history is preserved.';
  String get sourceArchived => _zh ? '来源已归档' : 'Source archived';
  String get sourceRestored =>
      _zh ? '来源已恢复但仍处于停用状态' : 'Source restored in a disabled state';
  String get nextRun => _zh ? '下次运行' : 'Next run';
  String get jobDiagnostics => _zh ? '任务结果' : 'Job result';
  String sourceSchedule(String mode, String time, String timezone) =>
      mode == 'daily'
      ? (_zh ? '每天 $time（$timezone）' : 'Daily at $time ($timezone)')
      : manualOnly;
  String nextRunAt(String value) => _zh ? '下次运行：$value' : 'Next run: $value';
  String jobResult(String value) => _zh ? '任务结果：$value' : 'Job result: $value';
  String get sourceNotFound =>
      _zh ? '找不到所选 Connector' : 'Selected Connector not found';
  String get requiredName => _zh ? '请填写来源名称' : 'Enter a source name';
  String operationFailed(Object error) =>
      _zh ? '操作失败：$error' : 'Operation failed: $error';
  String get authStatus => _zh ? '认证状态' : 'Authentication';
  String get checkAuth => _zh ? '检查认证' : 'Check authentication';
  String get beginAuth => _zh ? '开始认证' : 'Authenticate';
  String get manualSync => _zh ? '立即同步' : 'Sync now';
  String get queued => _zh ? '已排队' : 'Queued';
  String get running => _zh ? '运行中' : 'Running';
  String get completed => _zh ? '已完成' : 'Completed';
  String get failed => _zh ? '失败' : 'Failed';
  String get neverSynced => _zh ? '尚未成功同步' : 'Never synced successfully';
  String lastSynced(String value) =>
      _zh ? '上次同步：$value' : 'Last synced: $value';
  String get submit => _zh ? '提交' : 'Submit';
  String get openLoginPage => _zh ? '打开登录页面' : 'Open sign-in page';
  String get authReady => _zh ? '认证已就绪' : 'Authentication is ready';
  String get authStillRequired =>
      _zh ? '仍需完成认证' : 'Authentication still required';
  String authState(String state) => switch (state) {
    'not_required' => _zh ? '无需认证' : 'Not required',
    'auth_required' => _zh ? '需要认证' : 'Required',
    'waiting_for_user' => _zh ? '等待用户操作' : 'Waiting for you',
    'ready' => _zh ? '已就绪' : 'Ready',
    'expired' => _zh ? '已失效' : 'Expired',
    'unknown' => _zh ? '未知' : 'Unknown',
    _ => state,
  };
  String jobState(String state) => switch (state) {
    'pending' => queued,
    'running' => running,
    'succeeded' => completed,
    'completed' => completed,
    'failed' => failed,
    _ => state,
  };
  String requiredField(String label) => _zh ? '请填写$label' : 'Enter $label';

  String get secretConfigHint => _zh
      ? '敏感值将在来源创建后的安全认证流程中输入，不会保存到普通配置。'
      : 'Enter this secret in the secure authentication flow after creating the source. It is never stored in ordinary configuration.';
  String selectField(String label) => _zh ? '请选择$label' : 'Select $label';
  String get listFieldHint =>
      _zh ? '每行或用逗号填写一个值' : 'One value per line or comma-separated';
  String minItems(String label, int minimum) => _zh
      ? '$label 至少需要 $minimum 项'
      : '$label requires at least $minimum items';
  String minLength(String label, int minimum) => _zh
      ? '$label 至少需要 $minimum 个字符'
      : '$label requires at least $minimum characters';
  String get invalidUrl => _zh
      ? '请输入不包含凭据的 HTTP(S) 地址'
      : 'Enter an HTTP(S) URL without embedded credentials';
  String get enterInteger => _zh ? '请输入整数' : 'Enter an integer';
  String get enterNumber => _zh ? '请输入数字' : 'Enter a number';
  String minimumValue(String label, num minimum) =>
      _zh ? '$label 不能小于 $minimum' : '$label must be at least $minimum';
  String maximumValue(String label, num maximum) =>
      _zh ? '$label 不能大于 $maximum' : '$label must be at most $maximum';
  String unsupportedField(String name, String type) => _zh
      ? '当前客户端不支持字段 $name 的类型 $type'
      : 'This client does not support $name with type $type';
  String cannotConfigure(String name) =>
      _zh ? '无法配置 $name' : 'Cannot configure $name';
  String unsupportedSchemaType(String type) =>
      _zh ? '不支持的 Schema 类型：$type' : 'Unsupported Schema type: $type';
}

class _CampusStringsDelegate extends LocalizationsDelegate<CampusStrings> {
  const _CampusStringsDelegate();

  @override
  bool isSupported(Locale locale) => CampusStrings.supportedLocales.any(
    (supported) => supported.languageCode == locale.languageCode,
  );

  @override
  Future<CampusStrings> load(Locale locale) =>
      SynchronousFuture(CampusStrings(locale));

  @override
  bool shouldReload(_CampusStringsDelegate old) => false;
}

extension CampusStringsContext on BuildContext {
  CampusStrings get strings => CampusStrings.of(this);
}
