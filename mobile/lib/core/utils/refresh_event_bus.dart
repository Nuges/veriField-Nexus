import 'dart:async';

/// Global event bus to trigger UI refreshes across the app.
class RefreshEventBus {
  static final _activityRefreshController = StreamController<void>.broadcast();
  static final _auditRefreshController = StreamController<void>.broadcast();

  /// Stream to listen for activity refresh events.
  static Stream<void> get onActivityRefresh => _activityRefreshController.stream;

  /// Stream to listen for audit task refreshes.
  static Stream<void> get onAuditRefresh => _auditRefreshController.stream;

  /// Trigger a refresh of the activity list.
  static void triggerActivityRefresh() {
    _activityRefreshController.add(null);
  }

  /// Trigger a refresh of the audit task list.
  static void triggerAuditRefresh() {
    _auditRefreshController.add(null);
  }
}
