import 'package:flutter/material.dart';

/// App-wide design tokens and theme configuration.
class AppTheme {
  AppTheme._();

  // ── Spacing ──────────────────────────────────────────────────────────────
  static const double space2 = 2;
  static const double space4 = 4;
  static const double space8 = 8;
  static const double space12 = 12;
  static const double space16 = 16;
  static const double space24 = 24;
  static const double space32 = 32;

  static const EdgeInsets screenPadding = EdgeInsets.all(space16);
  static const EdgeInsets cardPadding = EdgeInsets.all(space16);

  // ── Radius ───────────────────────────────────────────────────────────────
  static const double radiusSmall = 8;
  static const double radiusMedium = 12;
  static const double radiusLarge = 16;

  // ── Icon sizes ───────────────────────────────────────────────────────────
  /// Inline/decorative icons next to text (e.g. section headers, info rows).
  static const double iconSizeSmall = 14;

  /// Standard card and action icons.
  static const double iconSizeMedium = 20;

  /// Prominent icons (e.g. wallet, account in summary cards).
  static const double iconSizeLarge = 22;

  // ── Icon container sizes ─────────────────────────────────────────────────
  /// Compact icon box used in summary cards.
  static const double iconBoxSizeSmall = 36;

  /// Standard icon box used in list cards (accounts, categories, transactions).
  static const double iconBoxSize = 44;

  static final BorderRadius borderRadiusSmall = BorderRadius.circular(
    radiusSmall,
  );
  static final BorderRadius borderRadiusMedium = BorderRadius.circular(
    radiusMedium,
  );
  static final BorderRadius borderRadiusLarge = BorderRadius.circular(
    radiusLarge,
  );

  // ── Semantic colours ─────────────────────────────────────────────────────
  static const Color incomeColor = Color(0xFF2E7D32); // green[800]
  static const Color expenseColor = Color(0xFFC62828); // red[800]
  static const Color incomeColorLight = Color(0xFFE8F5E9); // green[50]
  static const Color expenseColorLight = Color(0xFFFFEBEE); // red[50]

  // ── ThemeData ────────────────────────────────────────────────────────────
  static ThemeData get light {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: Colors.deepPurple,
      brightness: Brightness.light,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,

      // AppBar
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 1,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
        titleTextStyle: TextStyle(
          color: colorScheme.onSurface,
          fontSize: 18,
          fontWeight: FontWeight.w600,
          letterSpacing: 0,
        ),
      ),

      // Cards
      cardTheme: CardThemeData(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: borderRadiusMedium,
          side: BorderSide(color: colorScheme.outlineVariant),
        ),
        margin: EdgeInsets.zero,
      ),

      // Input fields — outlined everywhere
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: colorScheme.surfaceContainerLow,
        border: OutlineInputBorder(
          borderRadius: borderRadiusSmall,
          borderSide: BorderSide(color: colorScheme.outline),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: borderRadiusSmall,
          borderSide: BorderSide(color: colorScheme.outline),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: borderRadiusSmall,
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: borderRadiusSmall,
          borderSide: BorderSide(color: colorScheme.error),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: borderRadiusSmall,
          borderSide: BorderSide(color: colorScheme.error, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: space16,
          vertical: space12,
        ),
      ),

      // Elevated buttons
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          elevation: 0,
          padding: const EdgeInsets.symmetric(
            horizontal: space24,
            vertical: space12,
          ),
          shape: RoundedRectangleBorder(borderRadius: borderRadiusSmall),
          minimumSize: const Size(0, 48),
        ),
      ),

      // Outlined buttons
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(
            horizontal: space24,
            vertical: space12,
          ),
          shape: RoundedRectangleBorder(borderRadius: borderRadiusSmall),
          minimumSize: const Size(0, 48),
        ),
      ),

      // Text buttons
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: borderRadiusSmall),
        ),
      ),

      // Dividers
      dividerTheme: DividerThemeData(
        color: colorScheme.outlineVariant,
        space: 1,
        thickness: 1,
      ),

      // List tiles
      listTileTheme: const ListTileThemeData(
        contentPadding: EdgeInsets.symmetric(
          horizontal: space16,
          vertical: space4,
        ),
      ),
    );
  }
}
