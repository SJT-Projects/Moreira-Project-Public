import 'package:flutter/material.dart';

class AnalizadorScreen extends StatefulWidget {
  const AnalizadorScreen({super.key});

  @override
  State<AnalizadorScreen> createState() => _AnalizadorScreenState();
}

class _AnalizadorScreenState extends State<AnalizadorScreen> {
  final TextEditingController _inputController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  void _analizarTexto() {
    if (_inputController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, ingresá un texto o enlace.')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    // Simulación temporal de espera de respuesta de la API
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Detector Anti-Estafas'),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Pegá acá el mensaje o enlace sospechoso:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16.0),
            
            // Entrada de texto
            TextField(
              controller: _inputController,
              maxLines: 5,
              style: const TextStyle(fontSize: 18.0),
              decoration: InputDecoration(
                hintText: 'Ejemplo: "Su cuenta ha sido suspendida, ingrese a http://..."',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12.0),
                ),
                filled: true,
                fillColor: Colors.grey[100],
              ),
            ),
            const SizedBox(height: 24.0),

            // BOTÓN GIGANTE: Analizar Mensaje
            ElevatedButton.icon(
              onPressed: _isLoading ? null : _analizarTexto,
              icon: _isLoading
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 3),
                    )
                  : const Icon(Icons.security, size: 28),
              label: Text(_isLoading ? 'ANALIZANDO...' : 'ANALIZAR MENSAJE'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blue[700],
                foregroundColor: Colors.white,
              ),
            ),
            const SizedBox(height: 32.0),

            const Divider(thickness: 2),
            const SizedBox(height: 16.0),

            // BOTONES DE NAVEGACIÓN
            const Text(
              'Otras secciones:',
              style: TextStyle(fontSize: 20.0, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16.0),

            OutlinedButton.icon(
              onPressed: () => Navigator.pushNamed(context, '/comunidad'),
              icon: const Icon(Icons.people, size: 28),
              label: const Text('Ver Alertas Comunitarias'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 55),
                textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(height: 12.0),

            OutlinedButton.icon(
              onPressed: () => Navigator.pushNamed(context, '/academia'),
              icon: const Icon(Icons.school, size: 28),
              label: const Text('Academia Anti-Estafas'),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(double.infinity, 55),
                textStyle: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ),
    );
  }
}