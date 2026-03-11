import 'package:flutter_riverpod/flutter_riverpod.dart';

class CameraDevice {
  final int id;
  final String name;
  final String streamUrl;
  final bool useSubStream;
  final int displayOrder;
  final double aspectRatio;

  const CameraDevice({
    required this.id,
    required this.name,
    required this.streamUrl,
    this.useSubStream = true,
    this.displayOrder = 0,
    this.aspectRatio = 16 / 9,
  });

  factory CameraDevice.fromJson(Map<String, dynamic> json) => CameraDevice(
        id: json['id'] as int,
        name: json['name'] as String,
        streamUrl: json['stream_url'] as String,
        useSubStream: json['use_sub_stream'] as bool? ?? true,
        displayOrder: json['display_order'] as int? ?? 0,
        aspectRatio: (json['aspect_ratio'] as num?)?.toDouble() ?? (16 / 9),
      );

  String fullStreamUrl(String serverUrl) => '$serverUrl$streamUrl';
}

class AppMetadata {
  final List<CameraDevice> cameras;
  final String serverUrl;
  final String deviceToken;

  const AppMetadata({
    required this.cameras,
    required this.serverUrl,
    required this.deviceToken,
  });

  AppMetadata copyWith({List<CameraDevice>? cameras}) => AppMetadata(
        cameras: cameras ?? this.cameras,
        serverUrl: serverUrl,
        deviceToken: deviceToken,
      );
}

class AppMetadataNotifier extends Notifier<AppMetadata?> {
  @override
  AppMetadata? build() => null;

  void set(AppMetadata metadata) => state = metadata;
  void clear() => state = null;
  void updateCameras(List<CameraDevice> cameras) {
    if (state != null) state = state!.copyWith(cameras: cameras);
  }
}

final appMetadataProvider =
    NotifierProvider<AppMetadataNotifier, AppMetadata?>(
  AppMetadataNotifier.new,
);
