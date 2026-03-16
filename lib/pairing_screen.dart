import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'connection_manager.dart';
import 'metadata.dart';
import 'metadata_capture_service.dart';
import 'pairing_service.dart';
import 'settings_repository.dart';

class PairingScreen extends ConsumerStatefulWidget {
  const PairingScreen({super.key});

  @override
  ConsumerState<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends ConsumerState<PairingScreen> {
  final _serverUrlController = TextEditingController();

  _ScreenState _state = const _EnterUrl();

  @override
  void dispose() {
    _serverUrlController.dispose();
    super.dispose();
  }

  Future<void> _startPairing(String serverUrl) async {
    final url = serverUrl.trimRight().replaceAll(RegExp(r'/$'), '');

    setState(() => _state = const _Loading('Connecting to server...'));

    final service = PairingService(url);
    final result = await service.requestCode();

    if (!mounted) return;

    result.fold(
      (code) {
        setState(() => _state = _Polling(
              serverUrl: url,
              code: code,
              statusMessage: 'Waiting for authorization...',
            ));
        _poll(url, code);
      },
      (error) => setState(() => _state = _Error(error.message)),
    );
  }

  void _poll(String serverUrl, PairCode code) {
    final service = PairingService(serverUrl);
    service.pollStatus(code.code).listen(
      (result) {
        if (!mounted) return;
        result.fold(
          (approved) {
            if (approved == null) return; // still pending, keep waiting
            _onApproved(serverUrl, approved);
          },
          (error) => setState(() => _state = _Error(error.message)),
        );
      },
    );
  }

  Future<void> _onApproved(String serverUrl, PairApproved approved) async {
    final repo = await SettingsRepository.create();
    await repo.setServerUrl(serverUrl);
    await repo.setDeviceToken(approved.deviceToken);

    if (!mounted) return;

    ref.read(appMetadataProvider.notifier).set(AppMetadata(
          serverUrl: serverUrl,
          deviceToken: approved.deviceToken,
          cameras: approved.cameras,
        ));

    setState(() => _state = const _Loading('Authorized! Loading cameras...'));

    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const CameraGridScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: switch (_state) {
          _EnterUrl() => _buildUrlEntry(),
          _ => Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(32),
                child: switch (_state) {
                  _EnterUrl() => const SizedBox.shrink(),
                  _Loading(message: final msg) => _buildLoading(msg),
                  _Polling(code: final code, statusMessage: final msg) =>
                    _buildPolling(code, msg),
                  _Error(message: final msg) => _buildError(msg),
                },
              ),
            ),
        },
      ),
    );
  }

  Widget _buildUrlEntry() {
    final typed = _serverUrlController.text;
    return Column(
      children: [
        Expanded(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 48),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SvgPicture.asset('assets/logo.svg', height: 80),
                  const SizedBox(height: 16),
                  const Text(
                    'Enter your server address to get started',
                    style: TextStyle(color: Colors.white54, fontSize: 14),
                  ),
                  const SizedBox(height: 40),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 20, vertical: 14),
                    decoration: BoxDecoration(
                      border: Border.all(color: Colors.white24),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text.rich(
                      TextSpan(children: [
                        const TextSpan(
                          text: 'http://',
                          style: TextStyle(color: Colors.white38),
                        ),
                        TextSpan(
                          text: typed.isEmpty ? '_' : typed,
                          style: TextStyle(
                              color: typed.isEmpty
                                  ? Colors.white24
                                  : Colors.white),
                        ),
                      ]),
                      style: const TextStyle(
                          fontSize: 20, fontFamily: 'monospace'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        Container(
          decoration: const BoxDecoration(
            color: Color(0xFF1C1C1E),
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          child: _TvUrlKeyboard(
            onChar: (c) =>
                setState(() => _serverUrlController.text += c),
            onBackspace: () {
              if (_serverUrlController.text.isNotEmpty) {
                setState(() {
                  _serverUrlController.text = _serverUrlController.text
                      .substring(0, _serverUrlController.text.length - 1);
                });
              }
            },
            onConnect: () =>
                _startPairing('http://${_serverUrlController.text}'),
          ),
        ),
      ],
    );
  }

  Widget _buildLoading(String message) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const CircularProgressIndicator(color: Colors.white),
        const SizedBox(height: 20),
        Text(message, style: const TextStyle(color: Colors.white54)),
      ],
    );
  }

  Widget _buildPolling(PairCode code, String statusMessage) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Text(
          'Authorize this device',
          style: TextStyle(
              color: Colors.white, fontSize: 24, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 8),
        const Text(
          'Enter this code in the admin panel or scan the QR code',
          style: TextStyle(color: Colors.white54, fontSize: 13),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        Text(
          code.code,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 48,
            fontWeight: FontWeight.bold,
            letterSpacing: 8,
            fontFeatures: [FontFeature.tabularFigures()],
          ),
        ),
        const SizedBox(height: 32),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
          ),
          child: QrImageView(
            data: code.qrPayload,
            version: QrVersions.auto,
            size: 180,
          ),
        ),
        const SizedBox(height: 32),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: Colors.white54),
            ),
            const SizedBox(width: 12),
            Text(statusMessage,
                style: const TextStyle(color: Colors.white54, fontSize: 13)),
          ],
        ),
      ],
    );
  }

  Widget _buildError(String message) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.error_outline, color: Colors.redAccent, size: 48),
        const SizedBox(height: 16),
        Text(message,
            style: const TextStyle(color: Colors.white70),
            textAlign: TextAlign.center),
        const SizedBox(height: 24),
        FilledButton(
          onPressed: () => setState(() => _state = const _EnterUrl()),
          child: const Text('Try again'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Placeholder camera grid — replaced in future phases with WebRTC streams
// ---------------------------------------------------------------------------

class CameraGridScreen extends ConsumerStatefulWidget {
  const CameraGridScreen({super.key});

  @override
  ConsumerState<CameraGridScreen> createState() => _CameraGridScreenState();
}

class _CameraGridScreenState extends ConsumerState<CameraGridScreen>
    with WidgetsBindingObserver {
  bool _syncing = false;
  Timer? _pollTimer;
  Timer? _healthTimer;
  int _reconnectSignal = 0;

  // Server health
  bool _serverOffline = false;
  int _healthFailCount = 0;

  // Coordinated stream failure detection
  final List<DateTime> _recentFailures = [];

  static const _pollInterval = Duration(seconds: 60);
  static const _healthInterval = Duration(seconds: 30);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _sync();
      _checkHealth();
      _pollTimer = Timer.periodic(_pollInterval, (_) => _sync());
      _healthTimer = Timer.periodic(_healthInterval, (_) => _checkHealth());
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _pollTimer?.cancel();
    _healthTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      setState(() => _reconnectSignal++);
      _checkHealth();
      _sync();
    }
  }

  Future<void> _checkHealth() async {
    final metadata = ref.read(appMetadataProvider);
    if (metadata == null) return;
    try {
      final resp = await http.get(
        Uri.parse('${metadata.serverUrl}/health'),
      ).timeout(const Duration(seconds: 5));
      final ok = resp.statusCode == 200;
      if (!mounted) return;
      setState(() {
        _healthFailCount = ok ? 0 : _healthFailCount + 1;
        _serverOffline = _healthFailCount >= 2;
      });
      if (ok) _pollCommands(metadata);
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _healthFailCount++;
        _serverOffline = _healthFailCount >= 2;
      });
    }
  }

  Future<void> _pollCommands(AppMetadata metadata) async {
    try {
      final resp = await http.get(
        Uri.parse('${metadata.serverUrl}/commands/pending'),
        headers: {'Authorization': 'Bearer ${metadata.deviceToken}'},
      ).timeout(const Duration(seconds: 5));
      if (!mounted || resp.statusCode != 200) return;

      final json = jsonDecode(resp.body) as Map<String, dynamic>;
      final commands = (json['commands'] as List).cast<Map<String, dynamic>>();
      for (final cmd in commands) {
        _executeCommand(cmd['command'] as String, cmd['id'] as int, metadata);
      }
    } catch (_) {}
  }

  void _executeCommand(String command, int id, AppMetadata metadata) {
    // Acknowledge first (fire-and-forget)
    http.post(
      Uri.parse('${metadata.serverUrl}/commands/$id/ack'),
      headers: {'Authorization': 'Bearer ${metadata.deviceToken}'},
    ).ignore();

    switch (command) {
      case 'reconnect':
        setState(() => _reconnectSignal++);
      case 'refresh':
        _sync();
      case 'reload':
        if (mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const CameraGridScreen()),
          );
        }
    }
  }

  void _onCameraConnected() {
    ScaffoldMessenger.of(context).clearSnackBars();
    if (!_serverOffline) return;
    // A live camera connection proves the server is reachable — clear immediately
    setState(() {
      _healthFailCount = 0;
      _serverOffline = false;
    });
  }

  void _onCameraFailed(CameraFailureReason reason) {
    final now = DateTime.now();
    _recentFailures.add(now);
    // Keep only failures in the last 8 seconds
    _recentFailures.removeWhere(
        (t) => now.difference(t) > const Duration(seconds: 8));
    if (_recentFailures.length >= 2 && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Multiple streams failed — stream relay may be offline'),
          duration: Duration(seconds: 5),
          backgroundColor: Color(0xFF5C1010),
        ),
      );
      _recentFailures.clear();
    }
  }

  Future<void> _sync() async {
    final metadata = ref.read(appMetadataProvider);
    if (metadata == null) return;
    setState(() => _syncing = true);
    final svc = MetadataCaptureService(
      serverUrl: metadata.serverUrl,
      deviceToken: metadata.deviceToken,
      ref: ref,
    );
    final result = await svc.syncCameras();
    if (!mounted) return;
    setState(() => _syncing = false);
    result.fold(
      (_) {},
      (err) {
        if (err.type.name == 'auth') {
          // Token revoked — go back to pairing
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: (_) => const PairingScreen()),
          );
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final metadata = ref.watch(appMetadataProvider);
    final cameras = metadata?.cameras ?? [];

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        titleSpacing: 16,
        title: Row(
          children: [
            SvgPicture.asset('assets/logo.svg', height: 28),
            const Spacer(),
            if (_syncing)
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white54),
              )
            else
              PopupMenuButton<String>(
                icon: const Icon(Icons.more_vert, color: Colors.white54),
                onSelected: (value) async {
                  if (value == 'refresh') {
                    _sync();
                  } else if (value == 'reconnect') {
                    setState(() => _reconnectSignal++);
                  } else if (value == 'unpair') {
                    final nav = Navigator.of(context);
                    final confirmed = await showDialog<bool>(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Unpair device'),
                        content: const Text(
                            'This will remove the device token and return to the pairing screen.'),
                        actions: [
                          TextButton(
                              onPressed: () => Navigator.pop(ctx, false),
                              child: const Text('Cancel')),
                          TextButton(
                              onPressed: () => Navigator.pop(ctx, true),
                              child: const Text('Unpair')),
                        ],
                      ),
                    );
                    if (confirmed == true && mounted) {
                      final repo = await SettingsRepository.create();
                      await repo.clear();
                      ref.read(appMetadataProvider.notifier).clear();
                      nav.pushReplacement(
                        MaterialPageRoute(
                            builder: (_) => const PairingScreen()),
                      );
                    }
                  }
                },
                itemBuilder: (_) => const [
                  PopupMenuItem(value: 'refresh', child: Text('Refresh')),
                  PopupMenuItem(value: 'reconnect', child: Text('Reconnect all')),
                  PopupMenuItem(
                      value: 'unpair', child: Text('Unpair device')),
                ],
              ),
          ],
        ),
      ),
      body: Column(
        children: [
          if (_serverOffline)
            Container(
              width: double.infinity,
              color: const Color(0xFF5C1010),
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: const Row(
                children: [
                  Icon(Icons.cloud_off, color: Colors.white70, size: 16),
                  SizedBox(width: 8),
                  Text(
                    'Server unreachable — streams may not update',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ],
              ),
            ),
          Expanded(
            child: cameras.isEmpty
                ? Center(
                    child: Text(
                      _syncing ? 'Loading cameras...' : 'No cameras configured',
                      style: const TextStyle(color: Colors.white54),
                    ),
                  )
                : _CameraGrid(
                    cameras: cameras,
                    serverUrl: metadata!.serverUrl,
                    deviceToken: metadata.deviceToken,
                    onCameraFailed: _onCameraFailed,
                    onCameraConnected: _onCameraConnected,
                    reconnectSignal: _reconnectSignal,
                  ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Camera grid — hero row (aspect > 2.5) + 3-column regular grid
// ---------------------------------------------------------------------------

class _CameraGrid extends StatelessWidget {
  final List<CameraDevice> cameras;
  final String serverUrl;
  final String deviceToken;
  final void Function(CameraFailureReason) onCameraFailed;
  final VoidCallback onCameraConnected;
  final int reconnectSignal;

  const _CameraGrid({
    required this.cameras,
    required this.serverUrl,
    required this.deviceToken,
    required this.onCameraFailed,
    required this.onCameraConnected,
    required this.reconnectSignal,
  });

  @override
  Widget build(BuildContext context) {
    final heroes = cameras.where((c) => c.aspectRatio > 2.5).toList();
    final regular = cameras.where((c) => c.aspectRatio <= 2.5).toList();

    return LayoutBuilder(builder: (_, constraints) {
      const pad = 8.0;
      const gap = 8.0;
      const cols = 3;

      final availW = constraints.maxWidth - pad * 2;
      final availH = constraints.maxHeight - pad * 2;

      // Natural (unconstrained) heights for heroes
      final heroNaturalH = heroes.map((c) => availW / c.aspectRatio).toList();
      final heroSectionNatural = heroNaturalH.isEmpty
          ? 0.0
          : heroNaturalH.reduce((a, b) => a + b) +
              gap * (heroes.length - 1) +
              (regular.isNotEmpty ? gap : 0.0);

      // Natural heights for regular grid
      final regRows = regular.isEmpty ? 0 : (regular.length / cols).ceil();
      final cellW = (availW - gap * (cols - 1)) / cols;
      final cellNaturalH = cellW * 9 / 16;
      final regSectionNatural = regRows == 0
          ? 0.0
          : regRows * cellNaturalH + gap * (regRows - 1);

      final totalNatural = heroSectionNatural + regSectionNatural;

      // Single scale factor so everything fits without scrolling
      final scale = (totalNatural > availH && totalNatural > 0)
          ? availH / totalNatural
          : 1.0;

      final scaledHeroH = heroNaturalH.map((h) => h * scale).toList();
      final scaledCellH = cellNaturalH * scale;
      final scaledGap = gap * scale;

      // Build children list imperatively for clarity
      final children = <Widget>[];

      for (int i = 0; i < heroes.length; i++) {
        children.add(SizedBox(
          height: scaledHeroH[i],
          child: FocusTraversalOrder(
            order: NumericFocusOrder(i.toDouble()),
            child: _CameraTile(
              key: ValueKey(heroes[i].id),
              camera: heroes[i],
              serverUrl: serverUrl,
              deviceToken: deviceToken,
              autofocus: i == 0,
              onFailed: onCameraFailed,
              onConnected: onCameraConnected,
              reconnectSignal: reconnectSignal,
            ),
          ),
        ));
        if (i < heroes.length - 1 || regular.isNotEmpty) {
          children.add(SizedBox(height: scaledGap));
        }
      }

      for (int row = 0; row < regRows; row++) {
        final rowChildren = <Widget>[];
        for (int col = 0; col < cols; col++) {
          if (col > 0) rowChildren.add(const SizedBox(width: gap));
          final idx = row * cols + col;
          rowChildren.add(Expanded(
            child: idx < regular.length
                ? FocusTraversalOrder(
                    order: NumericFocusOrder((heroes.length + idx).toDouble()),
                    child: _CameraTile(
                      key: ValueKey(regular[idx].id),
                      camera: regular[idx],
                      serverUrl: serverUrl,
                      deviceToken: deviceToken,
                      autofocus: heroes.isEmpty && idx == 0,
                      onFailed: onCameraFailed,
                      onConnected: onCameraConnected,
                      reconnectSignal: reconnectSignal,
                    ),
                  )
                : const SizedBox.shrink(),
          ));
        }
        children.add(SizedBox(
          height: scaledCellH,
          child: Row(children: rowChildren),
        ));
        if (row < regRows - 1) children.add(SizedBox(height: scaledGap));
      }

      return FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Padding(
          padding: const EdgeInsets.all(pad),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: children,
          ),
        ),
      );
    });
  }
}

// ---------------------------------------------------------------------------
// TV on-screen keyboard for URL entry
// ---------------------------------------------------------------------------

class _TvUrlKeyboard extends StatelessWidget {
  final void Function(String) onChar;
  final VoidCallback onBackspace;
  final VoidCallback onConnect;

  const _TvUrlKeyboard({
    required this.onChar,
    required this.onBackspace,
    required this.onConnect,
  });

  // Standard numpad layout
  static const _rows = [
    ['7', '8', '9'],
    ['4', '5', '6'],
    ['1', '2', '3'],
    ['.', '0', ':'],
  ];

  static const _btnSize = 64.0;
  static const _gap = 6.0;

  @override
  Widget build(BuildContext context) {
    return FocusTraversalGroup(
      policy: OrderedTraversalPolicy(),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int r = 0; r < _rows.length; r++)
            Padding(
              padding: const EdgeInsets.only(bottom: _gap),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (int c = 0; c < _rows[r].length; c++) ...[
                    if (c > 0) const SizedBox(width: _gap),
                    FocusTraversalOrder(
                      order: NumericFocusOrder((r * 3 + c).toDouble()),
                      child: SizedBox(
                        width: _btnSize,
                        child: _KeyButton(
                          label: _rows[r][c],
                          onPressed: () => onChar(_rows[r][c]),
                          autofocus: r == 0 && c == 0,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          const SizedBox(height: _gap),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              FocusTraversalOrder(
                order: const NumericFocusOrder(40),
                child: SizedBox(
                  width: _btnSize,
                  child: _KeyButton(label: '⌫', onPressed: onBackspace),
                ),
              ),
              const SizedBox(width: _gap),
              FocusTraversalOrder(
                order: const NumericFocusOrder(41),
                child: SizedBox(
                  width: _btnSize * 2 + _gap,
                  child: _KeyButton(
                    label: 'Connect',
                    onPressed: onConnect,
                    primary: true,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _KeyButton extends StatefulWidget {
  final String label;
  final VoidCallback onPressed;
  final bool primary;
  final bool autofocus;

  const _KeyButton({
    required this.label,
    required this.onPressed,
    this.primary = false,
    this.autofocus = false,
  });

  @override
  State<_KeyButton> createState() => _KeyButtonState();
}

class _KeyButtonState extends State<_KeyButton> {
  final _focus = FocusNode();
  bool _focused = false;

  @override
  void initState() {
    super.initState();
    _focus.addListener(() {
      if (mounted) setState(() => _focused = _focus.hasFocus);
    });
  }

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _focus,
      autofocus: widget.autofocus,
      onKeyEvent: (_, event) {
        if (event is KeyDownEvent &&
            (event.logicalKey == LogicalKeyboardKey.select ||
                event.logicalKey == LogicalKeyboardKey.enter)) {
          widget.onPressed();
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      },
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 100),
          padding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 8,
          ),
          decoration: BoxDecoration(
            color: widget.primary
                ? (Colors.blue)
                : (_focused ? Colors.white : Colors.white12),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: _focused ? Colors.white : Colors.transparent,
              width: 2,
            ),
          ),
          child: Text(
            widget.label,
            style: TextStyle(
              color: (!widget.primary && _focused) ? Colors.black : Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// State types
// ---------------------------------------------------------------------------

sealed class _ScreenState {
  const _ScreenState();
}

class _EnterUrl extends _ScreenState {
  const _EnterUrl();
}

class _Loading extends _ScreenState {
  final String message;
  const _Loading(this.message);
}

class _Polling extends _ScreenState {
  final String serverUrl;
  final PairCode code;
  final String statusMessage;
  const _Polling(
      {required this.serverUrl,
      required this.code,
      required this.statusMessage});
}

class _Error extends _ScreenState {
  final String message;
  const _Error(this.message);
}

// ---------------------------------------------------------------------------
// Camera tile with live WebRTC stream
// ---------------------------------------------------------------------------

class _CameraTile extends StatefulWidget {
  final CameraDevice camera;
  final String serverUrl;
  final String deviceToken;
  final bool autofocus;
  final void Function(CameraFailureReason)? onFailed;
  final VoidCallback? onConnected;
  final int reconnectSignal;

  const _CameraTile({
    super.key,
    required this.camera,
    required this.serverUrl,
    required this.deviceToken,
    this.autofocus = false,
    this.onFailed,
    this.onConnected,
    required this.reconnectSignal,
  });

  @override
  State<_CameraTile> createState() => _CameraTileState();
}

class _CameraTileState extends State<_CameraTile> {
  late final CameraConnection _conn;
  CameraConnectionState _connState = CameraConnectionState.idle;
  final _focusNode = FocusNode();
  bool _isFocused = false;
  bool _isTraditionalFocus = false;

  // Auto-reconnect
  static const _backoffSeconds = [5, 10, 20, 40, 60];
  int _reconnectAttempt = 0;
  int _reconnectCountdown = 0;
  Timer? _reconnectTimer;
  Timer? _countdownTimer;

  // Stale frame detection
  Timer? _staleTimer;
  int? _lastFramesDecoded;
  int _frozenChecks = 0;
  bool _streamFrozen = false;
  ScaffoldFeatureController<SnackBar, SnackBarClosedReason>? _frozenSnackBar;

  @override
  void initState() {
    super.initState();
    _conn = CameraConnection(
      cameraId: widget.camera.id,
      serverUrl: widget.serverUrl,
      deviceToken: widget.deviceToken,
    );
    _conn.onStateChanged = (s) {
      if (mounted) {
        setState(() => _connState = s);
        if (s == CameraConnectionState.connected) {
          widget.onConnected?.call();
          _startStaleCheck();
        } else if (s == CameraConnectionState.failed) {
          _stopStaleCheck();
          if (_conn.failureReason != null) {
            widget.onFailed?.call(_conn.failureReason!);
          }
          _scheduleReconnect();
        }
      }
    };
    _focusNode.addListener(() {
      if (mounted) setState(() => _isFocused = _focusNode.hasFocus);
    });
    _isTraditionalFocus =
        FocusManager.instance.highlightMode == FocusHighlightMode.traditional;
    FocusManager.instance.addHighlightModeListener(_onHighlightModeChanged);
    _connect();
  }

  // On Linux kiosk, retry indefinitely — cap at the longest backoff interval.
  static bool get _infiniteRetry =>
      defaultTargetPlatform == TargetPlatform.linux;

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _countdownTimer?.cancel();

    if (_reconnectAttempt >= _backoffSeconds.length) {
      if (!_infiniteRetry) {
        // Max attempts reached — wait for manual retry
        return;
      }
      // Kiosk: keep retrying at the longest interval forever
      _reconnectAttempt = _backoffSeconds.length - 1;
    }

    final delay = _backoffSeconds[_reconnectAttempt];
    setState(() => _reconnectCountdown = delay);

    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) { t.cancel(); return; }
      setState(() => _reconnectCountdown--);
    });

    _reconnectTimer = Timer(Duration(seconds: delay), () {
      _countdownTimer?.cancel();
      if (!mounted) return;
      _reconnectAttempt++;
      _reconnectNow();
    });
  }

  Future<void> _reconnectNow() async {
    if (!mounted) return;
    _stopStaleCheck();
    setState(() => _connState = CameraConnectionState.idle);
    await _conn.disconnect();
    await _conn.connect();
  }

  void _startStaleCheck() {
    _staleTimer?.cancel();
    _lastFramesDecoded = null;
    _frozenChecks = 0;
    _staleTimer = Timer.periodic(const Duration(seconds: 5), (_) async {
      final frames = await _conn.framesDecoded();
      if (!mounted || frames == null) return;
      if (_lastFramesDecoded != null && frames == _lastFramesDecoded) {
        _frozenChecks++;
        if (_frozenChecks == 2 && !_streamFrozen) {
          _streamFrozen = true;
          _frozenSnackBar = ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('${widget.camera.name}: stream may be frozen'),
            duration: const Duration(seconds: 10),
            backgroundColor: const Color(0xFF5C3A00),
          ));
        }
      } else {
        if (_streamFrozen) {
          _streamFrozen = false;
          _frozenSnackBar?.close();
          _frozenSnackBar = null;
        }
        _frozenChecks = 0;
      }
      _lastFramesDecoded = frames;
    });
  }

  void _stopStaleCheck() {
    _staleTimer?.cancel();
    _staleTimer = null;
    _lastFramesDecoded = null;
    _frozenChecks = 0;
    if (_streamFrozen) {
      _streamFrozen = false;
      _frozenSnackBar?.close();
      _frozenSnackBar = null;
    }
  }

  void _onHighlightModeChanged(FocusHighlightMode mode) {
    if (mounted) {
      setState(() {
        _isTraditionalFocus = mode == FocusHighlightMode.traditional;
      });
    }
  }

  @override
  void didUpdateWidget(_CameraTile oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.reconnectSignal != oldWidget.reconnectSignal) {
      _reconnectTimer?.cancel();
      _countdownTimer?.cancel();
      _reconnectAttempt = 0;
      _reconnectCountdown = 0;
      _reconnectNow();
    }
  }

  Future<void> _connect() async {
    await _conn.init();
    await _conn.connect();
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    _countdownTimer?.cancel();
    _staleTimer?.cancel();
    FocusManager.instance.removeHighlightModeListener(_onHighlightModeChanged);
    _focusNode.dispose();
    _conn.dispose();
    super.dispose();
  }

  Widget _buildFailedOverlay() {
    final (icon, message) = switch (_conn.failureReason) {
      CameraFailureReason.signalingError => (Icons.cloud_off, 'Server error'),
      CameraFailureReason.networkError   => (Icons.wifi_off, 'Network error'),
      CameraFailureReason.iceFailure     => (Icons.videocam_off, 'Stream unavailable'),
      _                                  => (Icons.signal_wifi_off, 'Unavailable'),
    };
    final attemptsLeft = _backoffSeconds.length - _reconnectAttempt;
    final autoRetrying = _reconnectTimer?.isActive ?? false;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: Colors.white38, size: 24),
        const SizedBox(height: 4),
        Text(message,
            style: const TextStyle(color: Colors.white38, fontSize: 10)),
        const SizedBox(height: 4),
        if (autoRetrying)
          Text(
            _infiniteRetry
                ? 'Retrying in ${_reconnectCountdown}s'
                : 'Retrying in ${_reconnectCountdown}s ($attemptsLeft left)',
            style: const TextStyle(color: Colors.white24, fontSize: 9),
          )
        else if (!_infiniteRetry)
          Text(
            attemptsLeft <= 0 ? 'Auto-retry exhausted' : '',
            style: const TextStyle(color: Colors.white24, fontSize: 9),
          ),
        TextButton(
          onPressed: () {
            _reconnectTimer?.cancel();
            _countdownTimer?.cancel();
            setState(() {
              _reconnectAttempt = 0;
              _reconnectCountdown = 0;
            });
            _reconnectNow();
          },
          child: const Text('Retry now',
              style: TextStyle(color: Colors.white54, fontSize: 11)),
        ),
      ],
    );
  }

  void _openFullScreen() {
    Navigator.of(context).push(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => _FullScreenCameraPage(
          camera: widget.camera,
          conn: _conn,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      focusNode: _focusNode,
      autofocus: widget.autofocus,
      onKeyEvent: (_, event) {
        if (event is KeyDownEvent &&
            (event.logicalKey == LogicalKeyboardKey.select ||
             event.logicalKey == LogicalKeyboardKey.enter)) {
          _openFullScreen();
          return KeyEventResult.handled;
        }
        return KeyEventResult.ignored;
      },
      child: GestureDetector(
        onDoubleTap: _openFullScreen,
        child: Stack(
          fit: StackFit.expand,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Stack(
              fit: StackFit.expand,
              children: [
          // Video layer — always present once renderer is initialised
          if (_connState != CameraConnectionState.idle)
            RTCVideoView(
              _conn.renderer,
              objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
            ),

          // Overlay: loading / error / placeholder
          if (_connState != CameraConnectionState.connected)
            Container(
              color: Colors.grey[900],
              child: Center(
                child: _connState == CameraConnectionState.failed
                    ? _buildFailedOverlay()
                    : const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white38),
                      ),
              ),
            ),

          // SD / HD badge — bottom right, above name bar
          Positioned(
            right: 6,
            bottom: 24,
            child: Icon(
              widget.camera.useSubStream ? Icons.sd : Icons.hd,
              size: 16,
              color: Colors.white54,
            ),
          ),

          // Camera name label at the bottom
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [Colors.black87, Colors.transparent],
                ),
              ),
              child: Text(
                widget.camera.name,
                style: const TextStyle(color: Colors.white, fontSize: 11),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ),
              ],
            ),
          ),
          // Focus ring — only in D-pad/keyboard mode, not touch
          if (_isFocused && _isTraditionalFocus)
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.white, width: 3),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
        ],
      ),
    ),
    );
  }
}

// ---------------------------------------------------------------------------
// Full-screen camera view — double-tap to close
// ---------------------------------------------------------------------------

class _FullScreenCameraPage extends StatefulWidget {
  final CameraDevice camera;
  final CameraConnection conn;

  const _FullScreenCameraPage({
    required this.camera,
    required this.conn,
  });

  @override
  State<_FullScreenCameraPage> createState() => _FullScreenCameraPageState();
}

class _FullScreenCameraPageState extends State<_FullScreenCameraPage> {
  @override
  void initState() {
    super.initState();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  }

  @override
  void dispose() {
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onDoubleTap: () => Navigator.of(context).pop(),
        child: Stack(
          fit: StackFit.expand,
          children: [
            RTCVideoView(
              widget.conn.renderer,
              objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
            ),
            // Camera name label at the bottom
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.bottomCenter,
                    end: Alignment.topCenter,
                    colors: [Colors.black87, Colors.transparent],
                  ),
                ),
                child: Text(
                  widget.camera.name,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
              ),
            ),
            Positioned(
              top: 16,
              left: 12,
              child: SafeArea(
                child: IconButton(
                  autofocus: true,
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.black45,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
