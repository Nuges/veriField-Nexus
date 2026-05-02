// =============================================================================
// VeriField Nexus — Activity Detail Screen
// =============================================================================
// Shows detailed view of a single activity with trust score breakdown,
// photo proof, GPS location, and anomaly flags.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';

class ActivityDetailScreen extends StatefulWidget {
  final String activityId;
  const ActivityDetailScreen({super.key, required this.activityId});

  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  Map<String, dynamic>? _activity;
  Map<String, dynamic>? _trustBreakdown;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadActivity();
  }

  Future<void> _loadActivity() async {
    try {
      final activity = await ApiService.get('/activities/${widget.activityId}');
      setState(() { _activity = activity; _isLoading = false; });

      // Load trust score breakdown
      try {
        final trust = await ApiService.get('/activities/${widget.activityId}/trust');
        setState(() => _trustBreakdown = trust);
      } catch (_) {}
    } catch (e) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Activity Detail')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.primary))
          : _activity == null
              ? const VFEmptyState(icon: Icons.error_outline, title: 'Not found', subtitle: 'Activity could not be loaded')
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Photo proof
                      if (_activity!['image_url'] != null) _buildPhoto(),
                      const SizedBox(height: AppSpacing.xl),

                      // Trust Score
                      _buildTrustScore(),
                      const SizedBox(height: AppSpacing.xl),

                      // Anomaly Warning
                      if (_activity!['status'] == 'flagged') ...[
                        _buildAnomalyWarning(),
                        const SizedBox(height: AppSpacing.xl),
                      ],

                      // Activity Info
                      _buildInfoCard(),
                      const SizedBox(height: AppSpacing.base),

                      // GPS Info
                      if (_activity!['latitude'] != null) _buildGpsCard(),
                      const SizedBox(height: AppSpacing.base),

                      // Trust Breakdown
                      if (_trustBreakdown != null) _buildTrustBreakdown(),
                    ],
                  ),
                ),
    );
  }

  Widget _buildPhoto() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
      child: CachedNetworkImage(
        imageUrl: _activity!['image_url'],
        height: 220,
        width: double.infinity,
        fit: BoxFit.cover,
        placeholder: (_, __) => Container(height: 220, color: AppColors.surface),
        errorWidget: (_, __, ___) => Container(
          height: 220, color: AppColors.surface,
          child: const Icon(Icons.broken_image, color: AppColors.textTertiary, size: 48),
        ),
      ),
    ).animate().fadeIn().scale(begin: const Offset(0.98, 0.98));
  }

  Widget _buildTrustScore() {
    final score = (_activity!['trust_score'] as num?)?.toDouble();
    final status = _activity!['status'] ?? 'pending';

    return VFCard(
      gradient: AppColors.cardGradient,
      child: Row(
        children: [
          TrustScoreGauge(score: score, size: 70),
          const SizedBox(width: AppSpacing.xl),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Trust Score', style: AppTypography.caption),
                const SizedBox(height: 4),
                Text(
                  score != null ? '${score.toInt()}/100' : 'Pending',
                  style: AppTypography.heading,
                ),
                const SizedBox(height: 4),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: _statusColor(status).withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    status.toUpperCase(),
                    style: AppTypography.caption.copyWith(
                      color: _statusColor(status),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAnomalyWarning() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.trustLow.withValues(alpha: 0.1),
        border: Border.all(color: AppColors.trustLow.withValues(alpha: 0.3)),
        borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.warning_amber_rounded, color: AppColors.trustLow),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Anomaly Detected', style: AppTypography.body.copyWith(color: AppColors.trustLow, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(
                  'The Trust Engine flagged this entry. Please verify your GPS location or retake the photo proof to improve the trust score.',
                  style: AppTypography.caption,
                ),
                const SizedBox(height: 8),
                ElevatedButton.icon(
                  onPressed: () {
                    // Navigate to re-take or edit
                  },
                  icon: const Icon(Icons.refresh_rounded, size: 16),
                  label: const Text('Resolve Anomaly'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.trustLow,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    textStyle: AppTypography.caption.copyWith(fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ).animate().fadeIn(delay: 150.ms);
  }

  Widget _buildInfoCard() {
    final type = _activity!['activity_type'] ?? 'other';
    String dateStr = '';
    try {
      dateStr = DateFormat('MMMM d, yyyy • h:mm a').format(DateTime.parse(_activity!['captured_at']));
    } catch (_) {}

    return VFCard(
      child: Column(
        children: [
          _infoRow('Type', type.toString().toUpperCase(), Icons.category_rounded),
          const Divider(height: 24),
          _infoRow('Captured', dateStr, Icons.access_time_rounded),
          if (_activity!['description'] != null) ...[
            const Divider(height: 24),
            _infoRow('Notes', _activity!['description'], Icons.notes_rounded),
          ],
        ],
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _buildGpsCard() {
    return VFCard(
      child: Column(
        children: [
          _infoRow(
            'GPS',
            '${(_activity!['latitude'] as num).toStringAsFixed(4)}, ${(_activity!['longitude'] as num).toStringAsFixed(4)}',
            Icons.gps_fixed_rounded,
          ),
          if (_activity!['gps_accuracy'] != null) ...[
            const Divider(height: 24),
            _infoRow('Accuracy', '${(_activity!['gps_accuracy'] as num).toStringAsFixed(1)}m', Icons.my_location_rounded),
          ],
        ],
      ),
    ).animate().fadeIn(delay: 300.ms);
  }

  Widget _buildTrustBreakdown() {
    return VFCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Trust Breakdown', style: AppTypography.title),
          const SizedBox(height: AppSpacing.base),
          _scoreBar('GPS Score', (_trustBreakdown!['gps_score'] as num).toDouble(), 30, AppColors.accent),
          const SizedBox(height: AppSpacing.md),
          _scoreBar('Image Score', (_trustBreakdown!['image_score'] as num).toDouble(), 35, AppColors.accentPurple),
          const SizedBox(height: AppSpacing.md),
          _scoreBar('Frequency Score', (_trustBreakdown!['frequency_score'] as num).toDouble(), 35, AppColors.primary),
        ],
      ),
    ).animate().fadeIn(delay: 400.ms);
  }

  Widget _scoreBar(String label, double value, double max, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: AppTypography.bodySmall),
            Text('${value.toInt()}/${max.toInt()}', style: AppTypography.caption.copyWith(color: color)),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: value / max,
            backgroundColor: AppColors.surface,
            color: color,
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _infoRow(String label, String value, IconData icon) {
    return Row(
      children: [
        Icon(icon, size: 18, color: AppColors.textTertiary),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: AppTypography.caption),
              Text(value, style: AppTypography.body),
            ],
          ),
        ),
      ],
    );
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'verified': return AppColors.trustHigh;
      case 'review': return AppColors.trustMedium;
      case 'flagged': return AppColors.trustLow;
      default: return AppColors.textTertiary;
    }
  }
}
