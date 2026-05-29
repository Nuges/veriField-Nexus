// =============================================================================
// VeriField Nexus — Community Feed Screen (Live API)
// =============================================================================
// Displays the community validation feed fetched from the backend API.
// Includes interactive Likes and expandable technical nested Comments threads.
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

  // Local session state mapping
  final Set<String> _likedPostIds = {};
  final Set<String> _expandedPostIds = {};
  final Map<String, TextEditingController> _commentControllers = {};

  @override
  void initState() {
    super.initState();
    _loadFeed();
  }

  @override
  void dispose() {
    for (var controller in _commentControllers.values) {
      controller.dispose();
    }
    super.dispose();
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

  String _formatTime(String timestamp) {
    try {
      final date = DateTime.parse(timestamp);
      return DateFormat('h:mm a').format(date);
    } catch (_) {
      return '';
    }
  }

  Future<void> _handleUpvote(String postId, Map<String, dynamic> post) async {
    if (_likedPostIds.contains(postId)) return;

    // Optimistic UI updates
    setState(() {
      _likedPostIds.add(postId);
      post['upvotes'] = (post['upvotes'] ?? 0) + 1;
    });

    try {
      await ApiService.post('/community/$postId/upvote');
    } catch (e) {
      // Revert local modifications on failure
      setState(() {
        _likedPostIds.remove(postId);
        post['upvotes'] = ((post['upvotes'] ?? 1) - 1).clamp(0, 999999);
      });
      if (mounted) {
        VFNotification.showError(context, 'Like failed: $e');
      }
    }
  }

  Future<void> _handleSubmitComment(String postId, Map<String, dynamic> post) async {
    final controller = _commentControllers[postId];
    final text = controller?.text.trim() ?? '';
    if (text.isEmpty) return;

    // Clear text field immediately for instant feedback
    controller?.clear();

    try {
      final commentResponse = await ApiService.post(
        '/community/$postId/comments',
        body: {'comment': text},
      );

      setState(() {
        final currentComments = post['comments'] as List? ?? [];
        post['comments'] = [...currentComments, commentResponse];
        _expandedPostIds.add(postId);
      });

      if (mounted) {
        VFNotification.showSuccess(context, 'Reply posted successfully! 🚀');
      }
    } catch (e) {
      if (mounted) {
        VFNotification.showError(context, 'Failed to post reply: $e');
      }
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
    
    final postId = post['id']?.toString() ?? '';
    final isLiked = _likedPostIds.contains(postId);
    final isExpanded = _expandedPostIds.contains(postId);
    final comments = post['comments'] as List? ?? [];
    final commentCount = comments.length;

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
            
            // Engagement Actions Row
            Row(
              children: [
                // Upvote Button
                InkWell(
                  onTap: () => _handleUpvote(postId, post),
                  borderRadius: BorderRadius.circular(AppSpacing.sm),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 6.0),
                    child: Row(
                      children: [
                        Icon(
                          isLiked ? Icons.thumb_up : Icons.thumb_up_outlined,
                          size: 18,
                          color: isLiked ? AppColors.primary : AppColors.textSecondary,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '$upvotes',
                          style: AppTypography.caption.copyWith(
                            color: isLiked ? AppColors.primary : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.lg),
                
                // Reply/Drawer Button
                InkWell(
                  onTap: () {
                    setState(() {
                      if (isExpanded) {
                        _expandedPostIds.remove(postId);
                      } else {
                        _expandedPostIds.add(postId);
                      }
                    });
                  },
                  borderRadius: BorderRadius.circular(AppSpacing.sm),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 6.0),
                    child: Row(
                      children: [
                        Icon(
                          Icons.comment_outlined,
                          size: 18,
                          color: isExpanded ? AppColors.primary : AppColors.textSecondary,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          commentCount > 0 ? '$commentCount Replies' : 'Reply',
                          style: AppTypography.caption.copyWith(
                            color: isExpanded ? AppColors.primary : AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),

            // Nested Expanded Comment Thread Drawer
            if (isExpanded) ...[
              const SizedBox(height: AppSpacing.md),
              const Divider(height: 1),
              const SizedBox(height: AppSpacing.md),
              
              // Comments List
              if (comments.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.only(left: 8.0),
                  child: Column(
                    children: comments.map<Widget>((c) {
                      final cName = c['user_name'] ?? 'Unknown';
                      final cRole = c['user_role'] ?? 'member';
                      final cText = c['comment'] ?? '';
                      final cTime = c['timestamp'];
                      
                      String cRoleLabel = 'Member';
                      if (cRole == 'admin') cRoleLabel = 'Admin';
                      if (cRole == 'field_agent') cRoleLabel = 'Agent';
                      
                      return Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                        child: Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(AppSpacing.md),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceLight,
                            borderRadius: BorderRadius.circular(AppSpacing.radiusMd),
                            border: Border.all(color: AppColors.border.withValues(alpha: 0.1)),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                children: [
                                  Row(
                                    children: [
                                      Text(
                                        cName,
                                        style: AppTypography.title.copyWith(fontSize: 12),
                                      ),
                                      const SizedBox(width: 6),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                                        decoration: BoxDecoration(
                                          color: AppColors.surface,
                                          borderRadius: BorderRadius.circular(2),
                                        ),
                                        child: Text(
                                          cRoleLabel,
                                          style: AppTypography.caption.copyWith(fontSize: 8, fontWeight: FontWeight.bold),
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (cTime != null)
                                    Text(
                                      _formatTime(cTime.toString()),
                                      style: AppTypography.caption.copyWith(fontSize: 9),
                                    ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              Text(
                                cText,
                                style: AppTypography.bodySmall,
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
              ] else ...[
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                  child: Text(
                    'No replies yet. Be the first to start the thread!',
                    style: AppTypography.caption.copyWith(fontStyle: FontStyle.italic),
                  ),
                ),
              ],
              
              const SizedBox(height: AppSpacing.sm),
              // Write a reply input field
              Padding(
                padding: const EdgeInsets.only(left: 8.0),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _commentControllers.putIfAbsent(
                          postId, 
                          () => TextEditingController()
                        ),
                        style: AppTypography.bodySmall,
                        decoration: InputDecoration(
                          hintText: 'Write a technical response...',
                          hintStyle: AppTypography.caption,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                          filled: true,
                          fillColor: AppColors.surfaceLight,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                            borderSide: BorderSide.none,
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(AppSpacing.radiusLg),
                            borderSide: const BorderSide(color: AppColors.primary, width: 1),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    IconButton(
                      icon: const Icon(Icons.send_rounded, color: AppColors.primary),
                      onPressed: () => _handleSubmitComment(postId, post),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    ).animate()
        .fadeIn(delay: Duration(milliseconds: 50 * index))
        .slideX(begin: 0.05);
  }
}
