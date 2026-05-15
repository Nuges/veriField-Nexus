import 'dart:async';

/// Global event bus to trigger UI refreshes across the app.
class RefreshEventBus {
  static final _activityRefreshController = StreamController<void>.broadcast();

  /// Stream to listen for activity refresh events.
  static Stream<void> get onActivityRefresh => _activityRefreshController.stream;

  /// Trigger a refresh of the activity list.
  static void triggerActivityRefresh() {
    _activityRefreshController.add(null);
  }
}
