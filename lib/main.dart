import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'metadata.dart';
import 'pairing_screen.dart';
import 'settings_repository.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  runApp(const ProviderScope(child: _AppLoader()));
}

class _AppLoader extends StatefulWidget {
  const _AppLoader();

  @override
  State<_AppLoader> createState() => _AppLoaderState();
}

class _AppLoaderState extends State<_AppLoader> {
  SettingsRepository? _settings;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final settings = await SettingsRepository.create();
    // On Android TV, the launcher overlay takes ~4s to clear, so we hold the
    // Flutter splash long enough for it to be visible. On other devices the
    // native splash handles it and we transition immediately.
    if (await _isAndroidTv()) {
      await Future.delayed(const Duration(milliseconds: 5000));
    }
    if (mounted) setState(() => _settings = settings);
  }

  Future<bool> _isAndroidTv() async {
    if (defaultTargetPlatform != TargetPlatform.android) return false;
    final info = await DeviceInfoPlugin().androidInfo;
    return info.systemFeatures.contains('android.software.leanback');
  }

  @override
  Widget build(BuildContext context) {
    final settings = _settings;
    if (settings == null) {
      return const MaterialApp(
        debugShowCheckedModeBanner: false,
        home: _SplashScreen(),
      );
    }
    return WardenApp(settings: settings);
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: SizedBox(
          width: 200,
          height: 200,
          child: _SplashLogo(),
        ),
      ),
    );
  }
}

class _SplashLogo extends StatelessWidget {
  const _SplashLogo();

  @override
  Widget build(BuildContext context) {
    return Image.asset('assets/splash_logo.png');
  }
}

class WardenApp extends ConsumerWidget {
  final SettingsRepository settings;

  const WardenApp({super.key, required this.settings});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // If already paired, seed metadata from persisted settings
    if (settings.isPaired) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(appMetadataProvider.notifier).set(AppMetadata(
              serverUrl: settings.serverUrl!,
              deviceToken: settings.deviceToken!,
              cameras: const [],
            ));
      });
    }

    return MaterialApp(
      title: 'Warden',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blueGrey,
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: settings.isPaired ? const CameraGridScreen() : const PairingScreen(),
    );
  }
}
