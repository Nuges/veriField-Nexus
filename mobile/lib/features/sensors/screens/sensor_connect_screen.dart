// =============================================================================
// VeriField Nexus — Sensor Connect Screen (Live API)
// =============================================================================
// Displays connected IoT sensor devices fetched from the backend API.
// No hardcoded data — fully production-ready.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';
import 'dart:math' as math;

class SensorConnectScreen extends StatefulWidget {
  const SensorConnectScreen({super.key});

  @override
  State<SensorConnectScreen> createState() => _SensorConnectScreenState();
}

class _SensorConnectScreenState extends State<SensorConnectScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _scanController;
  bool _isScanning = false;
  bool _isLoading = true;
  String? _error;

  List<Map<String, dynamic>> _devices = [];

  @override
  void initState() {
    super.initState();
    _scanController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    _loadDevices();
  }

  @override
  void dispose() {
    _scanController.dispose();
    super.dispose();
  }

  Future<void> _loadDevices() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await ApiService.get('/sensors/devices');
      final devicesList = response['devices'] as List? ?? [];
      setState(() {
        _devices = devicesList.cast<Map<String, dynamic>>();
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _toggleScan() {
    setState(() {
      _isScanning = !_isScanning;
      if (_isScanning) {
        _scanController.repeat();
        // Refresh device list when scanning
        _loadDevices().then((_) {
          if (mounted) {
            setState(() {
              _isScanning = false;
              _scanController.stop();
            });
          }
        });
      } else {
        _scanController.stop();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('IoT Sensors', style: AppTypography.title),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDevices,
          ),
        ],
      ),
      body: Column(
        children: [
          _buildScannerHeader(),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(color: AppColors.primary),
                  )
                : _error != null
                    ? _buildErrorState()
                    : _devices.isEmpty
                        ? VFEmptyState(
                            icon: Icons.sensors_off,
                            title: 'No devices found',
                            subtitle:
                                'No IoT sensor devices have reported data yet. Connect a device to get started.',
                          )
                        : RefreshIndicator(
                            onRefresh: _loadDevices,
                            color: AppColors.primary,
                            child: ListView.builder(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              itemCount: _devices.length,
                              itemBuilder: (context, index) {
                                return _buildDeviceCard(
                                    _devices[index], index);
                              },
                            ),
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
      decoration: const BoxDecoration(
        color: AppColors.surfaceLight,
        border: Border(bottom: BorderSide(color: AppColors.border)),
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
                      progress:
                          _isScanning ? _scanController.value : 0.0,
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
                  color:
                      _isScanning ? AppColors.primary : AppColors.surface,
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
          const SizedBox(height: AppSpacing.md),
          // Device count summary
          Text(
            '${_devices.length} device${_devices.length == 1 ? '' : 's'} registered',
            style: AppTypography.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          VFButton(
            label: _isScanning ? 'Scanning...' : 'Refresh Devices',
            onPressed: _isScanning ? null : _toggleScan,
            icon: _isScanning ? Icons.stop_rounded : Icons.search_rounded,
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off, size: 64, color: AppColors.textTertiary),
            const SizedBox(height: AppSpacing.md),
            Text('Could not load devices', style: AppTypography.title),
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error ?? 'Unknown error',
              style: AppTypography.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            VFButton(label: 'Retry', onPressed: _loadDevices, icon: Icons.refresh),
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceCard(Map<String, dynamic> device, int index) {
    final deviceId = device['device_id'] ?? 'Unknown';
    final propertyName = device['property_name'] ?? 'Unlinked';
    final readingCount = device['reading_count'] ?? 0;
    final lastTemp = device['last_temperature'];
    final lastBattery = device['last_battery_voltage'];
    final usageRate = device['usage_rate'];

    // Determine battery status
    final batteryOk = lastBattery == null || lastBattery > 3.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(
                Icons.sensors_rounded,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(deviceId, style: AppTypography.title),
                  const SizedBox(height: 2),
                  Text(
                    '$propertyName • $readingCount readings',
                    style: AppTypography.caption,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      if (lastTemp != null) ...[
                        Icon(
                          Icons.thermostat,
                          size: 14,
                          color: AppColors.warning,
                        ),
                        const SizedBox(width: 4),
                        Text('${lastTemp.toStringAsFixed(1)}°C',
                            style: AppTypography.caption),
                        const SizedBox(width: 12),
                      ],
                      if (lastBattery != null) ...[
                        Icon(
                          batteryOk
                              ? Icons.battery_full
                              : Icons.battery_alert,
                          size: 14,
                          color: batteryOk
                              ? AppColors.trustHigh
                              : AppColors.error,
                        ),
                        const SizedBox(width: 4),
                        Text('${lastBattery.toStringAsFixed(1)}V',
                            style: AppTypography.caption),
                        const SizedBox(width: 12),
                      ],
                      if (usageRate != null) ...[
                        const Icon(Icons.show_chart,
                            size: 14, color: AppColors.accent),
                        const SizedBox(width: 4),
                        Text('${usageRate.toStringAsFixed(0)}% active',
                            style: AppTypography.caption),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ).animate()
        .fadeIn(delay: Duration(milliseconds: 50 * index))
        .slideX(begin: 0.05);
  }
}

// =============================================================================
// Radar Painter — Visual scan animation
// =============================================================================
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
        ).createShader(
            Rect.fromCircle(center: center, radius: maxRadius))
        ..style = PaintingStyle.fill;

      canvas.drawCircle(center, maxRadius, sweepPaint);
    }
  }

  @override
  bool shouldRepaint(RadarPainter oldDelegate) {
    return oldDelegate.progress != progress;
  }
}
