import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'error_handler.dart';
import 'metadata.dart';

class MetadataCaptureService {
  final String serverUrl;
  final String deviceToken;
  final WidgetRef ref;

  MetadataCaptureService({
    required this.serverUrl,
    required this.deviceToken,
    required this.ref,
  });

  /// Fetches the current camera list from the backend and updates [appMetadataProvider].
  Future<Result<List<CameraDevice>>> syncCameras() async {
    try {
      final resp = await http.get(
        Uri.parse('$serverUrl/streams/cameras'),
        headers: {'Authorization': 'Bearer $deviceToken'},
      ).timeout(const Duration(seconds: 10));

      if (resp.statusCode == 401) {
        return Result.err(AppError.auth('Device token rejected'));
      }
      if (resp.statusCode != 200) {
        return Result.err(
            AppError.server('Server returned ${resp.statusCode}'));
      }

      final list = jsonDecode(resp.body) as List;
      final cameras = list
          .map((c) => CameraDevice.fromJson(c as Map<String, dynamic>))
          .toList();

      ref.read(appMetadataProvider.notifier).updateCameras(cameras);
      return Result.ok(cameras);
    } on Exception catch (e) {
      return Result.err(AppError.network(e.toString()));
    }
  }
}
