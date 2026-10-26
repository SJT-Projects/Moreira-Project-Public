import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Emoji decorativo. Los lectores de pantalla lo saltean porque siempre va
/// acompañado de un texto que dice lo mismo.
class Emoji extends StatelessWidget {
  const Emoji(this.emoji, {super.key, this.size = 28});

  final String emoji;
  final double size;

  @override
  Widget build(BuildContext context) => ExcludeSemantics(
    child: Text(emoji, style: TextStyle(fontSize: size, height: 1.1)),
  );
}

/// Emoji dentro de un círculo de color suave, para encabezados y tarjetas.
class EmojiBadge extends StatelessWidget {
  const EmojiBadge(
    this.emoji, {
    super.key,
    this.size = 56,
    this.background = AppColors.durazno,
  });

  final String emoji;
  final double size;
  final Color background;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    alignment: Alignment.center,
    decoration: BoxDecoration(color: background, shape: BoxShape.circle),
    child: Emoji(emoji, size: size * 0.5),
  );
}

/// Encabezado de pantalla o sección: emoji grande, título y una bajada.
class SectionHeader extends StatelessWidget {
  const SectionHeader({
    required this.emoji,
    required this.title,
    this.subtitle,
    this.large = true,
    super.key,
  });

  final String emoji;
  final String title;
  final String? subtitle;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        EmojiBadge(emoji, size: large ? 64 : 52),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Semantics(
                header: true,
                child: Text(
                  title,
                  style: large
                      ? theme.textTheme.headlineSmall
                      : theme.textTheme.titleLarge,
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 6),
                Text(
                  subtitle!,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: AppColors.textoSuave,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

enum BannerKind { error, warning, info, success }

/// Aviso con emoji + texto. El tipo se entiende por el emoji y el texto,
/// no solo por el color.
class InfoBanner extends StatelessWidget {
  const InfoBanner({
    required this.message,
    this.kind = BannerKind.info,
    this.title,
    super.key,
  });

  final String message;
  final String? title;
  final BannerKind kind;

  @override
  Widget build(BuildContext context) {
    final (emoji, color, background) = switch (kind) {
      BannerKind.error => ('⛔', AppColors.rojo, AppColors.rojoFondo),
      BannerKind.warning => ('⚠️', AppColors.amarillo, AppColors.amarilloFondo),
      BannerKind.info => ('💡', AppColors.cafe, AppColors.mielClaro),
      BannerKind.success => ('✅', AppColors.verde, AppColors.verdeFondo),
    };
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: background,
        border: Border.all(color: color, width: 2),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Emoji(emoji, size: 26),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (title != null)
                  Text(
                    title!,
                    style: theme.textTheme.titleSmall?.copyWith(color: color),
                  ),
                Text(
                  message,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: kind == BannerKind.info ? AppColors.texto : color,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Mensaje centrado para estados vacíos o de error, con acción opcional.
class CenteredMessage extends StatelessWidget {
  const CenteredMessage({
    required this.emoji,
    required this.message,
    this.action,
    super.key,
  });

  final String emoji;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) => Center(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            EmojiBadge(emoji, size: 88),
            const SizedBox(height: 18),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            if (action != null) ...[const SizedBox(height: 20), action!],
          ],
        ),
      ),
    ),
  );
}
