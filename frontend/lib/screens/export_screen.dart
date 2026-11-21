import "package:flutter/material.dart";

import "package:expenis_mobile/models/export.dart";
import "package:expenis_mobile/service/export_delivery.dart";
import "package:expenis_mobile/service/export_service.dart";
import "package:expenis_mobile/theme.dart";
import "package:expenis_mobile/widgets/responsive.dart";

class ExportScreen extends StatefulWidget {
  const ExportScreen({super.key});

  @override
  State<ExportScreen> createState() => _ExportScreenState();
}

class _ExportScreenState extends State<ExportScreen> {
  final ExportService _service = ExportService();
  List<ExportAccount>? _accounts;
  String? _accountsError;
  String? _error;
  bool _loadingAccounts = true;
  bool _busy = false;
  bool _allDates = true;
  bool _allAccounts = true;
  DateTimeRange? _period;
  final Set<int> _selected = {};
  ExportFormat _format = ExportFormat.csv;

  ExportRequest get _request => ExportRequest(
    format: _format,
    dateFrom: _allDates ? null : _period?.start,
    dateTo: _allDates ? null : _period?.end,
    accountIds: _allAccounts ? null : Set.of(_selected),
  );
  String? get _validationError => !_allDates && _period == null
      ? "Выберите период"
      : _request.validationError;

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    setState(() {
      _loadingAccounts = true;
      _accountsError = null;
    });
    try {
      final accounts = await _service.fetchAccounts();
      if (!mounted) return;
      setState(() {
        _accounts = accounts;
        _loadingAccounts = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _accountsError = "Не удалось загрузить счета";
        _loadingAccounts = false;
      });
    }
  }

  Future<void> _choosePeriod() async {
    final now = DateUtils.dateOnly(DateTime.now());
    final period = await showDateRangePicker(
      context: context,
      firstDate: DateTime(1),
      lastDate: DateTime(9999, 12, 31),
      initialDateRange:
          _period ??
          DateTimeRange(start: DateTime(now.year, now.month), end: now),
      helpText: "Период экспорта",
      saveText: "Выбрать",
    );
    if (period != null && mounted) setState(() => _period = period);
  }

  Future<void> _export(BuildContext buttonContext) async {
    if (_busy || _validationError != null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    final request = _request;
    try {
      final file = await _service.export(request);
      if (!mounted || !buttonContext.mounted) return;
      final box = buttonContext.findRenderObject() as RenderBox?;
      final origin = box == null
          ? null
          : box.localToGlobal(Offset.zero) & box.size;
      final result = await deliverExport(file, origin: origin);
      if (!mounted) return;
      if (result != ExportDeliveryResult.cancelled) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result == ExportDeliveryResult.saved
                  ? "Файл сохранён"
                  : "Файл передан для скачивания или сохранения",
            ),
          ),
        );
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString().replaceFirst("Exception: ", ""));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colors = Theme.of(context).colorScheme;
    String date(DateTime value) =>
        "${value.day.toString().padLeft(2, "0")}.${value.month.toString().padLeft(2, "0")}.${value.year}";
    return Scaffold(
      appBar: AppBar(title: const Text("Экспорт операций")),
      body: ResponsiveCenter(
        child: ListView(
          padding: AppTheme.screenPadding,
          children: [
            Text("Ваша история — в таблице", style: textTheme.headlineSmall),
            const SizedBox(height: AppTheme.space8),
            const Text(
              "Выгрузите операции для анализа или переноса в другое приложение.",
            ),
            const SizedBox(height: AppTheme.space24),
            Text("Период", style: textTheme.titleMedium),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text("За всё время"),
              value: _allDates,
              onChanged: _busy
                  ? null
                  : (value) => setState(() => _allDates = value),
            ),
            if (!_allDates)
              OutlinedButton.icon(
                key: const Key("export-period"),
                onPressed: _busy ? null : _choosePeriod,
                icon: const Icon(Icons.date_range),
                label: Text(
                  _period == null
                      ? "Выбрать период"
                      : "${date(_period!.start)} — ${date(_period!.end)}",
                ),
              ),
            const Divider(height: 32),
            Text("Счета", style: textTheme.titleMedium),
            if (_loadingAccounts)
              const Center(child: CircularProgressIndicator())
            else if (_accountsError != null) ...[
              Text(_accountsError!, style: TextStyle(color: colors.error)),
              TextButton(
                onPressed: _loadAccounts,
                child: const Text("Повторить загрузку"),
              ),
            ] else ...[
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text("Все счета"),
                subtitle: const Text("Включая удалённые"),
                value: _allAccounts,
                onChanged: _busy
                    ? null
                    : (value) => setState(() => _allAccounts = value),
              ),
              if (!_allAccounts) ...[
                for (final account in _accounts!)
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(account.displayName),
                    subtitle: Text(account.currencyCode),
                    value: _selected.contains(account.id),
                    onChanged: _busy
                        ? null
                        : (value) => setState(() {
                            if (value == true) {
                              _selected.add(account.id);
                            } else {
                              _selected.remove(account.id);
                            }
                          }),
                  ),
              ],
              if (_accounts!.isEmpty)
                const Text(
                  "Счетов пока нет. Выгрузка будет содержать только заголовки.",
                ),
            ],
            const Divider(height: 32),
            Text("Формат файла", style: textTheme.titleMedium),
            const SizedBox(height: AppTheme.space12),
            SegmentedButton<ExportFormat>(
              segments: const [
                ButtonSegment(
                  value: ExportFormat.csv,
                  label: Text("CSV"),
                  icon: Icon(Icons.table_rows_outlined),
                ),
                ButtonSegment(
                  value: ExportFormat.xlsx,
                  label: Text("XLSX"),
                  icon: Icon(Icons.table_chart_outlined),
                ),
              ],
              selected: {_format},
              onSelectionChanged: _busy
                  ? null
                  : (value) => setState(() => _format = value.single),
            ),
            const SizedBox(height: AppTheme.space8),
            Text(
              _format == ExportFormat.csv
                  ? "Для импорта и обработки данных"
                  : "Для анализа в Excel и других таблицах",
              style: textTheme.bodySmall?.copyWith(
                color: colors.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppTheme.space24),
          ],
        ),
      ),
      bottomNavigationBar: SafeArea(
        top: false,
        child: Center(
          heightFactor: 1,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: Breakpoints.contentMaxWidth,
            ),
            child: Padding(
              padding: AppTheme.screenPadding,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_validationError != null &&
                      !_loadingAccounts &&
                      _accountsError == null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Text(
                        _validationError!,
                        style: TextStyle(color: colors.error),
                      ),
                    ),
                  if (_error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Semantics(
                        liveRegion: true,
                        child: Text(
                          _error!,
                          style: TextStyle(color: colors.error),
                        ),
                      ),
                    ),
                  Builder(
                    builder: (buttonContext) => FilledButton.icon(
                      key: const Key("export-submit"),
                      onPressed:
                          _busy ||
                              _loadingAccounts ||
                              _accountsError != null ||
                              _validationError != null
                          ? null
                          : () => _export(buttonContext),
                      icon: _busy
                          ? const SizedBox.square(
                              dimension: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.download_outlined),
                      label: Text(
                        _busy ? "Подготовка файла…" : "Экспортировать",
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
