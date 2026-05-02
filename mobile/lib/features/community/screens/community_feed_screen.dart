import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../shared/widgets/shared_widgets.dart';

class CommunityFeedScreen extends StatefulWidget {
  const CommunityFeedScreen({super.key});

  @override
  State<CommunityFeedScreen> createState() => _CommunityFeedScreenState();
}

class _CommunityFeedScreenState extends State<CommunityFeedScreen> {
  final List<Map<String, dynamic>> _posts = [
    {
      'id': 'p1',
      'user': 'Amina J.',
      'role': 'Community Leader',
      'action': 'validated an activity',
      'time': '2 hours ago',
      'content': 'I can confirm the new solar water pump in Sector 4 is operational. Good water flow observed this morning.',
      'upvotes': 12,
      'isUpvoted': false,
      'type': 'validation',
    },
    {
      'id': 'p2',
      'user': 'Musa K.',
      'role': 'Field Agent',
      'action': 'raised a flag',
      'time': '5 hours ago',
      'content': 'Notice: The cookstoves delivered to the north district are missing serial numbers. Pending manual verification.',
      'upvotes': 8,
      'isUpvoted': true,
      'type': 'flag',
    },
    {
      'id': 'p3',
      'user': 'Sarah O.',
      'role': 'Local Member',
      'action': 'shared an update',
      'time': '1 day ago',
      'content': 'Crop yields using the new sustainable fertilizer method are looking much healthier than last season.',
      'upvotes': 24,
      'isUpvoted': false,
      'type': 'update',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Community Feed', style: AppTypography.h3),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () {},
          ),
        ],
      ),
      body: ListView.builder(
        padding: const EdgeInsets.all(AppSpacing.md),
        itemCount: _posts.length,
        itemBuilder: (context, index) {
          return _buildPostCard(_posts[index]);
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {},
        backgroundColor: AppColors.primary,
        child: const Icon(Icons.add_comment, color: Colors.white),
      ),
    );
  }

  Widget _buildPostCard(Map<String, dynamic> post) {
    Color typeColor;
    IconData typeIcon;

    switch (post['type']) {
      case 'validation':
        typeColor = AppColors.trustHigh;
        typeIcon = Icons.check_circle;
        break;
      case 'flag':
        typeColor = AppColors.error;
        typeIcon = Icons.flag;
        break;
      default:
        typeColor = AppColors.primary;
        typeIcon = Icons.chat_bubble;
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
                    post['user'].substring(0, 1),
                    style: AppTypography.title.copyWith(color: AppColors.primary),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(post['user'], style: AppTypography.title.copyWith(fontSize: 16)),
                          const SizedBox(width: AppSpacing.sm),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppColors.backgroundAlt,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              post['role'],
                              style: AppTypography.caption.copyWith(fontSize: 10),
                            ),
                          ),
                        ],
                      ),
                      Text(
                        '${post['action']} • ${post['time']}',
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
              post['content'],
              style: AppTypography.bodyMedium,
            ),
            const SizedBox(height: AppSpacing.md),
            const Divider(height: 1),
            const SizedBox(height: AppSpacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    InkWell(
                      onTap: () {
                        setState(() {
                          post['isUpvoted'] = !post['isUpvoted'];
                          post['upvotes'] += post['isUpvoted'] ? 1 : -1;
                        });
                      },
                      child: Row(
                        children: [
                          Icon(
                            post['isUpvoted'] ? Icons.thumb_up : Icons.thumb_up_outlined,
                            size: 18,
                            color: post['isUpvoted'] ? AppColors.primary : AppColors.textSecondary,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            '${post['upvotes']}',
                            style: AppTypography.caption.copyWith(
                              color: post['isUpvoted'] ? AppColors.primary : AppColors.textSecondary,
                              fontWeight: post['isUpvoted'] ? FontWeight.bold : FontWeight.normal,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: AppSpacing.lg),
                    Row(
                      children: [
                        const Icon(Icons.comment_outlined, size: 18, color: AppColors.textSecondary),
                        const SizedBox(width: 4),
                        Text('Reply', style: AppTypography.caption),
                      ],
                    ),
                  ],
                ),
                TextButton(
                  onPressed: () {},
                  child: const Text('View Activity'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
