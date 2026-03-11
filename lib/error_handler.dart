enum AppErrorType { network, auth, server, notFound, unknown }

class AppError {
  final AppErrorType type;
  final String message;

  const AppError(this.type, this.message);

  factory AppError.network([String message = 'Network error']) =>
      AppError(AppErrorType.network, message);

  factory AppError.auth([String message = 'Authentication failed']) =>
      AppError(AppErrorType.auth, message);

  factory AppError.server([String message = 'Server error']) =>
      AppError(AppErrorType.server, message);

  factory AppError.notFound([String message = 'Not found']) =>
      AppError(AppErrorType.notFound, message);

  factory AppError.unknown([String message = 'Unknown error']) =>
      AppError(AppErrorType.unknown, message);

  @override
  String toString() => 'AppError($type): $message';
}

class Result<T> {
  final T? _value;
  final AppError? _error;

  const Result.ok(T value)
      : _value = value,
        _error = null;

  const Result.err(AppError error)
      : _value = null,
        _error = error;

  bool get isOk => _error == null;
  bool get isErr => _error != null;

  T get value => _value as T;
  AppError get error => _error!;

  R fold<R>(R Function(T) onOk, R Function(AppError) onErr) =>
      isOk ? onOk(_value as T) : onErr(_error!);
}
