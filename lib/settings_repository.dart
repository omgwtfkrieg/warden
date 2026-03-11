import 'package:shared_preferences/shared_preferences.dart';

class SettingsRepository {
  static const _serverUrlKey = 'server_url';
  static const _deviceTokenKey = 'device_token';

  final SharedPreferences _prefs;

  SettingsRepository(this._prefs);

  static Future<SettingsRepository> create() async {
    final prefs = await SharedPreferences.getInstance();
    return SettingsRepository(prefs);
  }

  String? get serverUrl => _prefs.getString(_serverUrlKey);
  String? get deviceToken => _prefs.getString(_deviceTokenKey);

  bool get isPaired => serverUrl != null && deviceToken != null;

  Future<void> setServerUrl(String url) => _prefs.setString(_serverUrlKey, url);
  Future<void> setDeviceToken(String token) =>
      _prefs.setString(_deviceTokenKey, token);

  Future<void> clear() async {
    await _prefs.remove(_serverUrlKey);
    await _prefs.remove(_deviceTokenKey);
  }
}
