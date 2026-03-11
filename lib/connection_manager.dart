import 'dart:async';

import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;

import 'error_handler.dart';

enum CameraConnectionState { idle, connecting, connected, failed }

enum CameraFailureReason { signalingError, networkError, iceFailure, unknown }

/// Manages the WebRTC connection lifecycle for a single camera stream.
/// SSoT for all connection logic — do not duplicate elsewhere.
class CameraConnection {
  final int cameraId;
  final String serverUrl;
  final String deviceToken;

  final RTCVideoRenderer renderer = RTCVideoRenderer();
  RTCPeerConnection? _pc;

  CameraConnectionState state = CameraConnectionState.idle;
  CameraFailureReason? failureReason;
  void Function(CameraConnectionState)? onStateChanged;

  CameraConnection({
    required this.cameraId,
    required this.serverUrl,
    required this.deviceToken,
  });

  Future<void> init() async {
    await renderer.initialize();
  }

  Future<Result<void>> connect() async {
    _setState(CameraConnectionState.connecting);

    try {
      final iceCompleter = Completer<void>();

      _pc = await createPeerConnection({
        'iceServers': [],
        'sdpSemantics': 'unified-plan',
      });

      _pc!.onTrack = (event) {
        if (event.streams.isNotEmpty) {
          renderer.srcObject = event.streams[0];
          _setState(CameraConnectionState.connected);
        }
      };

      _pc!.onConnectionState = (s) {
        if (s == RTCPeerConnectionState.RTCPeerConnectionStateFailed) {
          _setFailed(CameraFailureReason.iceFailure);
        }
      };

      // Set ICE gathering callbacks before creating the offer so we don't
      // miss the completion event.
      _pc!.onIceGatheringState = (s) {
        if (s == RTCIceGatheringState.RTCIceGatheringStateComplete &&
            !iceCompleter.isCompleted) {
          iceCompleter.complete();
        }
      };

      _pc!.onIceCandidate = (c) {
        // Null/empty candidate signals end-of-candidates.
        if ((c.candidate?.isEmpty ?? true) && !iceCompleter.isCompleted) {
          iceCompleter.complete();
        }
      };

      await _pc!.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly),
      );

      final offer = await _pc!.createOffer();
      await _pc!.setLocalDescription(offer);

      // go2rtc requires the full SDP with ICE candidates — wait for gathering.
      await iceCompleter.future
          .timeout(const Duration(seconds: 10), onTimeout: () {});

      final localDesc = await _pc!.getLocalDescription();
      if (localDesc?.sdp == null) {
        _setFailed(CameraFailureReason.unknown);
        return Result.err(AppError.server('Failed to build SDP offer'));
      }

      final resp = await http.post(
        Uri.parse('$serverUrl/streams/$cameraId/webrtc'),
        headers: {
          'Authorization': 'Bearer $deviceToken',
          'Content-Type': 'application/sdp',
        },
        body: localDesc!.sdp,
      ).timeout(const Duration(seconds: 15));

      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _setFailed(CameraFailureReason.signalingError);
        return Result.err(AppError.server('Stream returned ${resp.statusCode}'));
      }

      await _pc!.setRemoteDescription(
          RTCSessionDescription(resp.body, 'answer'));

      return Result.ok(null);
    } on Exception catch (e) {
      _setFailed(CameraFailureReason.networkError);
      return Result.err(AppError.network(e.toString()));
    }
  }

  Future<void> disconnect() async {
    renderer.srcObject = null;
    await _pc?.close();
    _pc = null;
    failureReason = null;
    _setState(CameraConnectionState.idle);
  }

  Future<void> dispose() async {
    await disconnect();
    await renderer.dispose();
  }

  void _setState(CameraConnectionState s) {
    state = s;
    onStateChanged?.call(s);
  }

  void _setFailed(CameraFailureReason reason) {
    failureReason = reason;
    _setState(CameraConnectionState.failed);
  }
}
