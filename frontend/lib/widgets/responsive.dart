import "package:flutter/material.dart";

/// Layout breakpoints shared by adaptive screens (Material 3 window classes).
class Breakpoints {
  Breakpoints._();

  /// From this width the bottom navigation bar becomes a side rail.
  static const double medium = 840;

  /// Lists and forms stop growing past this width.
  static const double contentMaxWidth = 720;

  /// Wide dashboards (statistics) stop growing past this width.
  static const double dashboardMaxWidth = 1280;

  /// From this content width dashboards split into two columns.
  static const double twoColumnMinWidth = 900;
}

/// Centers [child] horizontally and caps its width so lists and forms do not
/// stretch edge to edge on desktop and web.
class ResponsiveCenter extends StatelessWidget {
  const ResponsiveCenter({
    super.key,
    required this.child,
    this.maxWidth = Breakpoints.contentMaxWidth,
  });

  final Widget child;
  final double maxWidth;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}
