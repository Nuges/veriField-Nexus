import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import 'dart:math' as math;

class SensorConnectScreen extends StatefulWidget {
  const SensorConnectScreen({super.key});

  @override
  State<SensorConnectScreen> createState() => _SensorConnectScreenState();
}

class _SensorConnectScreenState extends State<SensorConnectScreen> with SingleTickerProviderStateMixin {
  late AnimationController _scanController;
  bool _isScanning = false;

  final List<Map<String, dynamic>> _devices = [
    {
      'id': 'd1',
      'name': 'CookStove IoT V2',
      'type': 'Thermal Sensor',
      'mac': '00:1A:2B:3C:4D:5E',
      'status': 'connected',
      'battery': 85,
      'signal': -45,
    },
    {
      'id': 'd2',
      'name': 'AgriSoil Moisture',
      'type': 'Soil Probe',
      'mac': 'A1:B2:C3:D4:E5:F6',
      'status': 'available',
      'battery': 92,
      'signal': -70,
    },
    {
      'id': 'd3',
      'name': 'Solar Panel Logger',
      'type': 'Energy Monitor',
      'mac': 'F1:E2:D3:C4:B5:A6',
      'status': 'available',
      'battery': 40,
      'signal': -85,
    },
  ];

  @override
  void initState() {
    super.initState();
    _scanController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
  }

  @override
  void dispose() {
    _scanController.dispose();
    super.dispose();
  }

  void _toggleScan() {
    setState(() {
      _isScanning = !_isScanning;
      if (_isScanning) {
        _scanController.repeat();
      } else {
        _scanController.stop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('IoT Sensors', style: AppTypography.h3),
        centerTitle: false,
      ),
      body: Column(
        children: [
          _buildScannerHeader(),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(AppSpacing.md),
              itemCount: _devices.length,
              itemBuilder: (context, index) {
                return _buildDeviceCard(_devices[index]);
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildScannerHeader() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.xl),
      decoration: BoxDecoration(
        color: AppColors.backgroundAlt,
        border: const Border(bottom: BorderSide(color: AppColors.border)),
      ),
      child: Column(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              AnimatedBuilder(
                animation: _scanController,
                builder: (context, child) {
                  return CustomPaint(
                    painter: RadarPainter(
                      progress: _isScanning ? _scanController.value : 0.0,
                      color: AppColors.primary,
                    ),
                    size: const Size(120, 120),
                  );
                },
              ),
              Container(
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  color: _isScanning ? AppColors.primary : AppColors.surface,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.primary, width: 2),
                  boxShadow: [
                    if (_isScanning)
                      BoxShadow(
                        color: AppColors.primary.withValues(alpha: 0.4),
                        blurRadius: 15,
                        spreadRadius: 5,
                      ),
                  ],
                ),
                child: Icon(
                  Icons.bluetooth,
                  size: 32,
                  color: _isScanning ? Colors.white : AppColors.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          VFButton(
            label: _isScanning ? 'Stop Scanning' : 'Scan for Devices',
            onPressed: _toggleScan,
            icon: _isScanning ? Icons.stop_rounded : Icons.search_rounded,
          ),
        ],
      ),
    );
  }

  Widget _buildDeviceCard(Map<String, dynamic> device) {
    final isConnected = device['status'] == 'connected';
    
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: isConnected 
                    ? AppColors.trustHigh.withValues(alpha: 0.1) 
                    : AppColors.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.sensors_rounded,
                color: isConnected ? AppColors.trustHigh : AppColors.primary,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(device['name'], style: AppTypography.title),
                  const SizedBox(height: 2),
                  Text('${device['type']} • ${device['mac']}', style: AppTypography.caption),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        device['battery'] > 20 ? Icons.battery_full : Icons.battery_alert,
                        size: 14,
                        color: device['battery'] > 20 ? AppColors.trustHigh : AppColors.error,
                      ),
                      const SizedBox(width: 4),
                      Text('${device['battery']}%', style: AppTypography.caption),
                      const SizedBox(width: 12),
                      Icon(
                        Icons.signal_cellular_alt,
                        size: 14,
                        color: _getSignalColor(device['signal']),
                      ),
                      const SizedBox(width: 4),
                      Text('${device['signal']} dBm', style: AppTypography.caption),
                    ],
                  ),
                ],
              ),
            ),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  device['status'] = isConnected ? 'available' : 'connected';
                });
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: isConnected ? AppColors.surface : AppColors.primary,
                foregroundColor: isConnected ? AppColors.error : Colors.white,
                elevation: 0,
                side: BorderSide(color: isConnected ? AppColors.error : AppColors.primary),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
              child: Text(isConnected ? 'Disconnect' : 'Connect'),
            ),
          ],
        ),
      ),
    );
  }

  Color _getSignalColor(int signal) {
    if (signal > -60) return AppColors.trustHigh;
    if (signal > -80) return AppColors.warning;
    return AppColors.error;
  }
}

class RadarPainter extends CustomPainter {
  final double progress;
  final Color color;

  RadarPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.width / 2;

    // Draw grid rings
    final Paint gridPaint = Paint()
      ..color = color.withValues(alpha: 0.1)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1;

    canvas.drawCircle(center, maxRadius * 0.33, gridPaint);
    canvas.drawCircle(center, maxRadius * 0.66, gridPaint);
    canvas.drawCircle(center, maxRadius, gridPaint);

    if (progress > 0) {
      // Draw radar sweep
      final sweepPaint = Paint()
        ..shader = SweepGradient(
          center: Alignment.center,
          startAngle: 0.0,
          endAngle: math.pi * 2,
          colors: [
            color.withValues(alpha: 0.0),
            color.withValues(alpha: 0.5),
          ],
          transform: GradientRotation(progress * math.pi * 2),
        ).createShader(Rect.fromCircle(center: center, radius: maxRadius))
        ..style = PaintingStyle.fill;

      canvas.drawCircle(center, maxRadius, sweepPaint);
    }
  }

  @override
  bool shouldRepaint(RadarPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
