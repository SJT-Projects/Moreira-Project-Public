import 'package:flutter/material.dart';

import '../models/analisis_result.dart';

/// Paleta cálida pensada para adultos mayores.
///
/// Todos los pares texto/fondo superan una relación de contraste de 4,5:1
/// (la mayoría está por encima de 6:1), así que se leen bien aun con poca
/// visión o con el brillo de la pantalla bajo.
class AppColors {
  AppColors._();

  // Base cálida: crema, terracota y marrón.
  static const crema = Color(0xFFFFF8F0);
  static const papel = Color(0xFFFFFDF9);
  static const terracota = Color(0xFF9A3B0E);
  static const durazno = Color(0xFFFFE2CC);
  static const cafe = Color(0xFF4A1D05);
  static const miel = Color(0xFF7A4B00);
  static const mielClaro = Color(0xFFFFEFC2);
  static const texto = Color(0xFF2B1D14);
  static const textoSuave = Color(0xFF5C4636);
  static const borde = Color(0xFF8A6E5A);
  static const bordeSuave = Color(0xFFE8D5C0);

  // Semáforo: el color nunca va solo, siempre acompaña un emoji y un texto.
  static const rojo = Color(0xFFB71C1C);
  static const rojoFondo = Color(0xFFFDECEA);
  static const amarillo = Color(0xFF8A4B00);
  static const amarilloFondo = Color(0xFFFFF4D6);
  static const verde = Color(0xFF1B6B33);
  static const verdeFondo = Color(0xFFE7F5EA);
  static const gris = Color(0xFF5C4636);
  static const grisFondo = Color(0xFFF3ECE6);
}

/// Cómo se muestra cada nivel de riesgo: color, fondo, emoji y una frase corta.
class RiskStyle {
  const RiskStyle({
    required this.color,
    required this.background,
    required this.emoji,
    required this.icon,
    required this.headline,
  });

  final Color color;
  final Color background;
  final String emoji;
  final IconData icon;
  final String headline;

  static RiskStyle of(RiskLevel risk) => switch (risk) {
    RiskLevel.high => const RiskStyle(
      color: AppColors.rojo,
      background: AppColors.rojoFondo,
      emoji: '🔴',
      icon: Icons.gpp_bad_outlined,
      headline: '¡Cuidado! Parece una estafa',
    ),
    RiskLevel.medium => const RiskStyle(
      color: AppColors.amarillo,
      background: AppColors.amarilloFondo,
      emoji: '🟡',
      icon: Icons.warning_amber_rounded,
      headline: 'Ojo: hay señales sospechosas',
    ),
    RiskLevel.low => const RiskStyle(
      color: AppColors.verde,
      background: AppColors.verdeFondo,
      emoji: '🟢',
      icon: Icons.verified_user_outlined,
      headline: 'No encontramos señales de estafa',
    ),
    RiskLevel.unknown => const RiskStyle(
      color: AppColors.gris,
      background: AppColors.grisFondo,
      emoji: '⚪',
      icon: Icons.help_outline,
      headline: 'No pudimos terminar la revisión',
    ),
  };
}

ThemeData buildAppTheme() {
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: AppColors.terracota,
    onPrimary: Colors.white,
    primaryContainer: AppColors.durazno,
    onPrimaryContainer: AppColors.cafe,
    secondary: AppColors.miel,
    onSecondary: Colors.white,
    secondaryContainer: AppColors.mielClaro,
    onSecondaryContainer: AppColors.cafe,
    tertiary: AppColors.verde,
    onTertiary: Colors.white,
    tertiaryContainer: AppColors.verdeFondo,
    onTertiaryContainer: AppColors.texto,
    error: AppColors.rojo,
    onError: Colors.white,
    errorContainer: AppColors.rojoFondo,
    onErrorContainer: AppColors.texto,
    surface: AppColors.crema,
    onSurface: AppColors.texto,
    onSurfaceVariant: AppColors.textoSuave,
    surfaceContainerLowest: Colors.white,
    surfaceContainerLow: AppColors.papel,
    surfaceContainer: AppColors.papel,
    surfaceContainerHigh: Color(0xFFFFF1E2),
    surfaceContainerHighest: Color(0xFFFBE9D7),
    outline: AppColors.borde,
    outlineVariant: AppColors.bordeSuave,
  );

  // Tipografía grande: nada por debajo de 16 px y el texto común en 18–20 px.
  // Los tamaños escalan con la configuración de texto del sistema.
  const textTheme = TextTheme(
    displaySmall: TextStyle(
      fontSize: 36,
      fontWeight: FontWeight.bold,
      height: 1.2,
    ),
    headlineMedium: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.bold,
      height: 1.25,
    ),
    headlineSmall: TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.bold,
      height: 1.25,
    ),
    titleLarge: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.bold,
      height: 1.3,
    ),
    titleMedium: TextStyle(
      fontSize: 21,
      fontWeight: FontWeight.w700,
      height: 1.3,
    ),
    titleSmall: TextStyle(
      fontSize: 19,
      fontWeight: FontWeight.w700,
      height: 1.3,
    ),
    bodyLarge: TextStyle(fontSize: 20, height: 1.5),
    bodyMedium: TextStyle(fontSize: 18, height: 1.5),
    bodySmall: TextStyle(fontSize: 16, height: 1.45),
    labelLarge: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
    labelMedium: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
    labelSmall: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
  );

  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    textTheme: textTheme.apply(
      bodyColor: AppColors.texto,
      displayColor: AppColors.texto,
    ),
    scaffoldBackgroundColor: AppColors.crema,
    visualDensity: VisualDensity.comfortable,
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );

  final roundedLarge = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(18),
  );
  const buttonText = TextStyle(fontSize: 20, fontWeight: FontWeight.w700);
  const buttonPadding = EdgeInsets.symmetric(horizontal: 24, vertical: 16);

  return base.copyWith(
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.terracota,
      foregroundColor: Colors.white,
      centerTitle: false,
      toolbarHeight: 72,
      titleTextStyle: TextStyle(
        fontSize: 24,
        fontWeight: FontWeight.bold,
        color: Colors.white,
      ),
      iconTheme: IconThemeData(size: 30, color: Colors.white),
      actionsIconTheme: IconThemeData(size: 30, color: Colors.white),
    ),
    cardTheme: CardThemeData(
      color: AppColors.papel,
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: const BorderSide(color: AppColors.bordeSuave, width: 1.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(64, 60),
        padding: buttonPadding,
        textStyle: buttonText,
        shape: roundedLarge,
        iconSize: 28,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        minimumSize: const Size(64, 60),
        padding: buttonPadding,
        textStyle: buttonText,
        shape: roundedLarge,
        iconSize: 28,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(64, 60),
        padding: buttonPadding,
        textStyle: buttonText,
        shape: roundedLarge,
        iconSize: 28,
        foregroundColor: AppColors.terracota,
        side: const BorderSide(color: AppColors.terracota, width: 2),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(64, 56),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        textStyle: buttonText.copyWith(decoration: TextDecoration.underline),
        foregroundColor: AppColors.terracota,
        iconSize: 26,
      ),
    ),
    iconButtonTheme: IconButtonThemeData(
      style: IconButton.styleFrom(
        minimumSize: const Size(56, 56),
        iconSize: 30,
      ),
    ),
    floatingActionButtonTheme: FloatingActionButtonThemeData(
      backgroundColor: AppColors.terracota,
      foregroundColor: Colors.white,
      extendedTextStyle: buttonText,
      extendedSizeConstraints: const BoxConstraints(minHeight: 64),
      extendedPadding: const EdgeInsets.symmetric(horizontal: 24),
      shape: roundedLarge,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      labelStyle: const TextStyle(fontSize: 19, color: AppColors.textoSuave),
      floatingLabelStyle: const TextStyle(
        fontSize: 19,
        color: AppColors.terracota,
        fontWeight: FontWeight.w600,
      ),
      hintStyle: const TextStyle(fontSize: 18, color: AppColors.textoSuave),
      helperStyle: const TextStyle(fontSize: 16, color: AppColors.textoSuave),
      counterStyle: const TextStyle(fontSize: 16, color: AppColors.textoSuave),
      errorStyle: const TextStyle(fontSize: 17, color: AppColors.rojo),
      prefixIconColor: AppColors.textoSuave,
      suffixIconColor: AppColors.textoSuave,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borde, width: 1.5),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.borde, width: 1.5),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.terracota, width: 3),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.rojo, width: 2),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.rojo, width: 3),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      height: 92,
      backgroundColor: AppColors.papel,
      indicatorColor: AppColors.durazno,
      indicatorShape: roundedLarge,
      labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
      // El seleccionado se distingue también por el peso de la letra, no solo
      // por el color.
      labelTextStyle: WidgetStateProperty.resolveWith(
        (states) => TextStyle(
          fontSize: 18,
          color: states.contains(WidgetState.selected)
              ? AppColors.cafe
              : AppColors.textoSuave,
          fontWeight: states.contains(WidgetState.selected)
              ? FontWeight.w800
              : FontWeight.w500,
        ),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      backgroundColor: AppColors.mielClaro,
      labelStyle: const TextStyle(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        color: AppColors.cafe,
      ),
      side: BorderSide.none,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: AppColors.papel,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      titleTextStyle: textTheme.titleLarge?.copyWith(color: AppColors.texto),
      contentTextStyle: textTheme.bodyMedium?.copyWith(color: AppColors.texto),
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: AppColors.texto,
      contentTextStyle: TextStyle(fontSize: 19, color: Colors.white),
      showCloseIcon: true,
      closeIconColor: Colors.white,
    ),
    listTileTheme: const ListTileThemeData(
      minVerticalPadding: 12,
      titleTextStyle: TextStyle(
        fontSize: 19,
        fontWeight: FontWeight.w600,
        color: AppColors.texto,
      ),
      subtitleTextStyle: TextStyle(fontSize: 18, color: AppColors.textoSuave),
    ),
    checkboxTheme: CheckboxThemeData(
      side: const BorderSide(color: AppColors.borde, width: 2),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
    ),
    dividerTheme: const DividerThemeData(
      color: AppColors.bordeSuave,
      thickness: 1.5,
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: AppColors.terracota,
    ),
    expansionTileTheme: const ExpansionTileThemeData(
      textColor: AppColors.texto,
      collapsedTextColor: AppColors.texto,
      iconColor: AppColors.terracota,
      collapsedIconColor: AppColors.terracota,
    ),
  );
}
