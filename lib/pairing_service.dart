import 'dart:convert';
import 'dart:math';

import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'error_handler.dart';
import 'metadata.dart';

class PairCode {
  final String code;
  final String qrPayload;
  final DateTime expiresAt;

  const PairCode({
    required this.code,
    required this.qrPayload,
    required this.expiresAt,
  });
}

class PairApproved {
  final String deviceToken;
  final List<CameraDevice> cameras;

  const PairApproved({required this.deviceToken, required this.cameras});
}

/// Collects a stable hardware identifier and human-readable model name.
/// Returns (hardwareId, deviceModel). Both may be null if unavailable.
Future<(String?, String?)> _deviceInfo() async {
  try {
    final info = DeviceInfoPlugin();
    if (defaultTargetPlatform == TargetPlatform.android) {
      final android = await info.androidInfo;
      // androidId is stable per device+signature; resets on factory reset
      final hwId = android.id;
      final model = '${android.brand} ${android.model}'.trim();
      return (hwId.isEmpty ? null : hwId, model.isEmpty ? null : model);
    }
  } catch (_) {}
  return (null, null);
}

class PairingService {
  final String serverUrl;

  PairingService(this.serverUrl);

  Future<Result<PairCode>> requestCode() async {
    final (hwId, deviceModel) = await _deviceInfo();

    try {
      final resp = await http
          .post(
            Uri.parse('$serverUrl/pair/request'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              if (hwId != null) 'hardware_id': hwId,
              if (deviceModel != null) 'device_model': deviceModel,
            }),
          )
          .timeout(const Duration(seconds: 10));

      if (resp.statusCode == 200) {
        final json = jsonDecode(resp.body) as Map<String, dynamic>;
        return Result.ok(PairCode(
          code: json['code'] as String,
          qrPayload: json['qr_payload'] as String,
          expiresAt: DateTime.parse(json['expires_at'] as String),
        ));
      }
      return Result.err(AppError.server('Server returned ${resp.statusCode}'));
    } on Exception catch (e) {
      return Result.err(AppError.network(e.toString()));
    }
  }

  /// Polls until approved, expired, or [maxAttempts] reached.
  /// Uses exponential backoff starting at 1s, capped at 10s.
  /// Yields null while pending, PairApproved when done, or an error.
  Stream<Result<PairApproved?>> pollStatus(String code,
      {int maxAttempts = 60}) async* {
    var delay = 1.0;

    for (var i = 0; i < maxAttempts; i++) {
      await Future.delayed(Duration(milliseconds: (delay * 1000).toInt()));
      delay = min(delay * 1.5, 10.0);

      try {
        final resp = await http
            .get(
              Uri.parse('$serverUrl/pair/status')
                  .replace(queryParameters: {'code': code}),
            )
            .timeout(const Duration(seconds: 10));

        if (resp.statusCode != 200) {
          yield Result.err(
              AppError.server('Server returned ${resp.statusCode}'));
          return;
        }

        final json = jsonDecode(resp.body) as Map<String, dynamic>;
        final statusStr = json['status'] as String;

        if (statusStr == 'expired') {
          yield Result.err(AppError.auth('Pairing code expired'));
          return;
        }

        if (statusStr == 'approved') {
          final cameras = (json['cameras'] as List)
              .map((c) => CameraDevice.fromJson(c as Map<String, dynamic>))
              .toList();
          yield Result.ok(PairApproved(
            deviceToken: json['device_token'] as String,
            cameras: cameras,
          ));
          return;
        }

        // still pending
        yield const Result.ok(null);
      } on Exception catch (e) {
        yield Result.err(AppError.network(e.toString()));
        return;
      }
    }

    yield Result.err(AppError.auth('Pairing timed out'));
  }
}
