import "dart:async";

import "package:flutter/material.dart";

import "package:expenis_mobile/models/personal_greeting.dart";
import "package:expenis_mobile/service/personal_greeting_service.dart";
import "package:expenis_mobile/service/settings_service.dart";

class PersonalGreetingBanner extends StatefulWidget {
  final bool active;
  final int refreshRevision;

  const PersonalGreetingBanner({
    super.key,
    this.active = true,
    this.refreshRevision = 0,
  });

  @override
  State<PersonalGreetingBanner> createState() => _PersonalGreetingBannerState();
}

class _PersonalGreetingBannerState extends State<PersonalGreetingBanner>
    with WidgetsBindingObserver {
  final _service = PersonalGreetingService();
  PersonalGreeting? _greeting;
  String? _closingId;
  bool _loadError = false;
  int _request = 0;
  Timer? _expiryTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    SettingsService.sessionRevision.addListener(_sessionChanged);
    if (widget.active) _load();
  }

  @override
  void didUpdateWidget(PersonalGreetingBanner oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!widget.active) {
      _request++;
      _expiryTimer?.cancel();
      _greeting = null;
      _loadError = false;
    } else if (!oldWidget.active ||
        oldWidget.refreshRevision != widget.refreshRevision) {
      _load();
    }
  }

  void _sessionChanged() {
    _request++;
    _expiryTimer?.cancel();
    setState(() {
      _greeting = null;
      _closingId = null;
      _loadError = false;
    });
    if (widget.active) _load();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && widget.active) _load();
  }

  bool _current(int request, int session) =>
      mounted &&
      widget.active &&
      request == _request &&
      session == SettingsService.sessionRevision.value;

  Future<void> _load() async {
    final request = ++_request;
    final session = SettingsService.sessionRevision.value;
    _expiryTimer?.cancel();
    setState(() {
      _greeting = null;
      _loadError = false;
    });
    try {
      final settings = await SettingsService.getInstance();
      if (!await settings.hasAccessToken() || !_current(request, session)) {
        return;
      }
      final greeting = await _service.fetchGreeting();
      if (!_current(request, session)) return;
      final expiry = greeting?.expiresAt;
      if (expiry != null && !expiry.isAfter(DateTime.now().toUtc())) return;
      setState(() => _greeting = greeting);
      if (expiry != null) {
        _expiryTimer = Timer(expiry.difference(DateTime.now().toUtc()), () {
          if (_current(request, session)) setState(() => _greeting = null);
        });
      }
    } catch (_) {
      if (_current(request, session)) setState(() => _loadError = true);
    }
  }

  Future<void> _dismiss(PersonalGreeting greeting) async {
    final session = SettingsService.sessionRevision.value;
    setState(() => _closingId = greeting.id);
    try {
      await _service.dismissGreeting(greeting.id);
      if (!mounted || session != SettingsService.sessionRevision.value) return;
      // Invalidate reads begun before dismissal; reload may reveal a replacement.
      if (widget.active) {
        await _load();
      } else {
        _request++;
      }
    } catch (_) {
      if (!mounted || session != SettingsService.sessionRevision.value) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text("Could not close greeting. Please try again."),
          action: SnackBarAction(
            label: "Retry",
            onPressed: () {
              if (mounted &&
                  _greeting?.id == greeting.id &&
                  _closingId == null) {
                _dismiss(greeting);
              }
            },
          ),
        ),
      );
    } finally {
      if (mounted && session == SettingsService.sessionRevision.value) {
        setState(() => _closingId = null);
      }
    }
  }

  @override
  void dispose() {
    _expiryTimer?.cancel();
    SettingsService.sessionRevision.removeListener(_sessionChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.active) return const SizedBox.shrink();
    if (_loadError) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          children: [
            const Expanded(child: Text("Could not load greeting.")),
            TextButton(onPressed: _load, child: const Text("Retry")),
          ],
        ),
      );
    }
    final greeting = _greeting;
    if (greeting == null) return const SizedBox.shrink();
    return Card(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      color: Theme.of(context).colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.only(left: 16, top: 8, bottom: 8, right: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: ConstrainedBox(
                constraints: BoxConstraints(
                  maxHeight: MediaQuery.sizeOf(context).height * 0.22,
                ),
                child: SingleChildScrollView(
                  child: Text(
                    greeting.text,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSecondaryContainer,
                    ),
                  ),
                ),
              ),
            ),
            IconButton(
              tooltip: "Close greeting",
              onPressed: _closingId != null ? null : () => _dismiss(greeting),
              icon: const Icon(Icons.close),
            ),
          ],
        ),
      ),
    );
  }
}
