// =============================================================================
// VeriField Nexus — Community Feed Screen (Live API)
// =============================================================================
// Displays the community validation feed fetched from the backend API.
// No hardcoded data — fully production-ready.
// =============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:intl/intl.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';
import '../../../services/api_service.dart';

class CommunityFeedScreen extends StatefulWidget {
  const CommunityFeedScreen({super.key});

  @override
  State<CommunityFeedScreen> createState() => _CommunityFeedScreenState();
}

class _CommunityFeedScreenState extends State<CommunityFeedScreen> {
  List<Map<String, dynamic>> _posts = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadFeed();
  }

  Future<void> _loadFeed() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final response = await ApiService.get('/community?per_page=50');
      final postsList = response['posts'] as List? ?? [];
      setState(() {
        _posts = postsList.cast<Map<String, dynamic>>();
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Community Feed', style: AppTypography.title),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadFeed,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: AppColors.primary),
            )
          : _error != null
              ? _buildErrorState()
              : _posts.isEmpty
                  ? VFEmptyState(
                      icon: Icons.forum_outlined,
                      title: 'No community posts yet',
                      subtitle:
                          'Community validations and updates will appear here.',
                    )
                  : RefreshIndicator(
                      onRefresh: _loadFeed,
                      color: AppColors.primary,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        itemCount: _posts.length,
                        itemBuilder: (context, index) {
                          return _buildPostCard(_posts[index], index);
                        },
                      ),
                    ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Future: open a submission dialog
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Submit validations from the asset detail page')),
          );
        },
        backgroundColor: AppColors.primary,
        child: const Icon(Icons.add_comment, color: Colors.white),
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
            Text('Could not load feed', style: AppTypography.title),
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error ?? 'Unknown error',
              style: AppTypography.bodySmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.lg),
            VFButton(label: 'Retry', onPressed: _loadFeed, icon: Icons.refresh),
          ],
        ),
      ),
    );
  }

  Widget _buildPostCard(Map<String, dynamic> post, int index) {
    final response = post['response'] ?? 'pending';
    final userName = post['user_name'] ?? 'Unknown';
    final userRole = post['user_role'] ?? 'member';
    final action = post['action'] ?? 'shared an update';
    final content = post['content'] ?? '';
    final timestamp = post['timestamp'];
    final upvotes = post['upvotes'] ?? 0;

    // Determine type from response
    Color typeColor;
    IconData typeIcon;
    switch (response) {
      case 'yes':
        typeColor = AppColors.trustHigh;
        typeIcon = Icons.check_circle;
        break;
      case 'no':
        typeColor = AppColors.error;
        typeIcon = Icons.flag;
        break;
      default:
        typeColor = AppColors.primary;
        typeIcon = Icons.chat_bubble;
    }

    // Format timestamp
    String timeStr = '';
    if (timestamp != null) {
      try {
        final date = DateTime.parse(timestamp);
        final now = DateTime.now();
        final diff = now.difference(date);
        if (diff.inMinutes < 60) {
          timeStr = '${diff.inMinutes}m ago';
        } else if (diff.inHours < 24) {
          timeStr = '${diff.inHours}h ago';
        } else if (diff.inDays < 7) {
          timeStr = '${diff.inDays}d ago';
        } else {
          timeStr = DateFormat('MMM d').format(date);
        }
      } catch (_) {
        timeStr = '';
      }
    }

    // Role label formatting
    String roleLabel;
    switch (userRole) {
      case 'admin':
        roleLabel = 'Admin';
        break;
      case 'field_agent':
        roleLabel = 'Field Agent';
        break;
      default:
        roleLabel = 'Member';
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: VFCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: AppColors.primary.withValues(alpha: 0.2),
                  child: Text(
                    userName.isNotEmpty ? userName.substring(0, 1) : '?',
                    style: AppTypography.title
                        .copyWith(color: AppColors.primary),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(userName,
                                style: AppTypography.title
                                    .copyWith(fontSize: 16),
                                overflow: TextOverflow.ellipsis),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.surfaceLight,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              roleLabel,
                              style: AppTypography.caption
                                  .copyWith(fontSize: 10),
                            ),
                          ),
                        ],
                      ),
                      Text(
                        '$action${timeStr.isNotEmpty ? ' • $timeStr' : ''}',
                        style: AppTypography.caption,
                      ),
                    ],
                  ),
                ),
                Icon(typeIcon, color: typeColor, size: 20),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              content,
              style: AppTypography.body,
            ),
            const SizedBox(height: AppSpacing.md),
            const Divider(height: 1),
            const SizedBox(height: AppSpacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      upvotes > 0
                          ? Icons.thumb_up
                          : Icons.thumb_up_outlined,
                      size: 18,
                      color: upvotes > 0
                          ? AppColors.primary
                          : AppColors.textSecondary,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      '$upvotes',
                      style: AppTypography.caption.copyWith(
                        color: upvotes > 0
                            ? AppColors.primary
                            : AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.lg),
                    const Icon(Icons.comment_outlined,
                        size: 18, color: AppColors.textSecondary),
                    const SizedBox(width: 4),
                    Text('Reply', style: AppTypography.caption),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    ).animate()
        .fadeIn(delay: Duration(milliseconds: 50 * index))
        .slideX(begin: 0.05);
  }
}
