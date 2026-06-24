// =============================================================================
// VeriField Nexus — WBC/EBC QR Code Scanner (Simulated Interface)
// =============================================================================
// Premium visual mockup representing the camera barcode/QR scanner page.
// Animates a green scanner overlay, simulates detection of seeded codes,
// and supports manual key entry fallback for production robustness.
// =============================================================================

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';

class QrScannerScreen extends StatefulWidget {
  const QrScannerScreen({super.key});

  @override
  State<QrScannerScreen> createState() => _QrScannerScreenState();
}

class _QrScannerScreenState extends State<QrScannerScreen> {
  final TextEditingController _manualCodeController = TextEditingController();
  bool _isManualInputActive = false;
  bool _isScanSuccessful = false;
  String? _detectedCode;
  Timer? _simulationTimer;

  @override
  void initState() {
    super.initState();
    // Simulate active camera detection after 2.5 seconds
    _simulationTimer = Timer(const Duration(milliseconds: 2500), () {
      if (mounted && !_isManualInputActive) {
        setState(() {
          _isScanSuccessful = true;
          _detectedCode = 'CSI-EBC-BIO-9921';
        });
        // Auto-return the verified code after a short delay for feedback
        Timer(const Duration(milliseconds: 1200), () {
          if (mounted) {
            Navigator.pop(context, _detectedCode);
          }
        });
      }
    });
  }

  @override
  void dispose() {
    _simulationTimer?.cancel();
    _manualCodeController.dispose();
    super.dispose();
  }

  void _submitManualCode() {
    final code = _manualCodeController.text.trim();
    if (code.isNotEmpty) {
      Navigator.pop(context, code);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        title: const Text('Scan EBC/WBC QR Code', style: TextStyle(color: Colors.white)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded, color: Colors.white),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Stack(
        children: [
          // 1. Mock Camera View Background
          Positioned.fill(
            child: Container(
              color: Colors.grey[900],
              child: Center(
                child: Opacity(
                  opacity: 0.15,
                  child: Icon(Icons.camera_rounded, size: 100, color: Colors.grey[400]),
                ),
              ),
            ),
          ),

          // 2. Scanner Laser Line Animation (Simulated)
          if (!_isScanSuccessful && !_isManualInputActive)
            Positioned(
              left: 50,
              right: 50,
              top: MediaQuery.of(context).size.height * 0.25,
              child: Container(
                height: 4,
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.8),
                      blurRadius: 8,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ).animate(onPlay: (controller) => controller.repeat(reverse: true))
               .moveY(begin: 0, end: 200, duration: 1800.ms, curve: Curves.easeInOut),
            ),

          // 3. Scan Alignment Box Overlay
          Center(
            child: Container(
              width: 250,
              height: 250,
              decoration: BoxDecoration(
                border: Border.all(
                  color: _isScanSuccessful ? AppColors.primary : Colors.white54,
                  width: 3,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Stack(
                children: [
                  // Corner brackets styling
                  _buildCornerBracket(top: 0, left: 0, angle: 0),
                  _buildCornerBracket(top: 0, right: 0, angle: 90),
                  _buildCornerBracket(bottom: 0, left: 0, angle: 270),
                  _buildCornerBracket(bottom: 0, right: 0, angle: 180),
                  
                  // Scanning success indicator
                  if (_isScanSuccessful)
                    Center(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.9),
                          borderRadius: BorderRadius.circular(30),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.check_circle_outline_rounded, color: Colors.white, size: 20),
                            const SizedBox(width: 8),
                            Text('Code Detected!', style: AppTypography.bodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ).animate().scale(duration: 300.ms, curve: Curves.bounceOut),
                    ),
                ],
              ),
            ),
          ),

          // 4. Instructions and Manual Input Trigger
          Positioned(
            left: 20,
            right: 20,
            bottom: 40,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (!_isManualInputActive) ...[
                  Text(
                    _isScanSuccessful ? 'Verifying: $_detectedCode' : 'Align EBC/WBC certificate QR code inside frame.',
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  VFButton(
                    label: 'Enter Code Manually',
                    icon: Icons.keyboard_rounded,
                    isOutlined: true,
                    onPressed: () {
                      setState(() {
                        _isManualInputActive = true;
                        _simulationTimer?.cancel();
                      });
                    },
                  ),
                ] else ...[
                  // Manual input card
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('Manual Code Entry', style: AppTypography.title.copyWith(fontWeight: FontWeight.bold)),
                        const SizedBox(height: AppSpacing.sm),
                        TextField(
                          controller: _manualCodeController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            hintText: 'e.g. CSI-EBC-BIO-9921',
                            hintStyle: TextStyle(color: Colors.grey[600]),
                            fillColor: AppColors.background,
                            filled: true,
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(AppSpacing.radiusMd)),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.md),
                        Row(
                          children: [
                            Expanded(
                              child: TextButton(
                                onPressed: () {
                                  setState(() => _isManualInputActive = false);
                                },
                                child: const Text('Cancel'),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: VFButton(
                                label: 'Verify Code',
                                onPressed: _submitManualCode,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ).animate().slideY(begin: 0.2, duration: 250.ms),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCornerBracket({
    double? top,
    double? bottom,
    double? left,
    double? right,
    required double angle,
  }) {
    return Positioned(
      top: top,
      bottom: bottom,
      left: left,
      right: right,
      child: Transform.rotate(
        angle: angle * 3.14159 / 180,
        child: Container(
          width: 24,
          height: 24,
          decoration: const BoxDecoration(
            border: Border(
              top: BorderSide(color: AppColors.primary, width: 4),
              left: BorderSide(color: AppColors.primary, width: 4),
            ),
          ),
        ),
      ),
    );
  }
}
