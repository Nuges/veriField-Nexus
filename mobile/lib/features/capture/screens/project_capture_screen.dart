import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../core/utils/field_access.dart';
import '../../../services/api_service.dart';
import '../../activities/screens/activity_form_screen.dart';
import 'soil_collection_screen.dart';

/// Project records, rather than a methodology URL or a cookstove default, choose the form.
class ProjectCaptureScreen extends StatefulWidget {
  final String? projectId;
  const ProjectCaptureScreen({super.key, this.projectId});
  @override
  State<ProjectCaptureScreen> createState() => _ProjectCaptureScreenState();
}
class _ProjectCaptureScreenState extends State<ProjectCaptureScreen> {
  Map<String, dynamic>? _user;
  List<Map<String, dynamic>> _projects = [];
  String? _selectedId;
  String? _error;
  bool _loading = true;
  bool _open = false;
  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try {
      var user = ApiService.currentUser;
      try { user = await ApiService.get('/auth/me'); } catch (error) { if (error is ApiException && (error.statusCode == 401 || error.statusCode == 403)) rethrow; if (user == null) rethrow; }
      if (!FieldAccess.canCapture(user?['role'])) throw Exception('Your role cannot submit field records.');
      final actor = user;
      if (actor == null) throw Exception('Sign in before capturing field records.');
      final prefs = await SharedPreferences.getInstance();
      final key = 'capture_projects:${actor['organization_id']}:${actor['id']}';
      List<dynamic> items;
      try {
        final response = await ApiService.get('/projects');
        items = (response['items'] ?? response['data'] ?? []) as List;
        await prefs.setString(key, jsonEncode(items));
      } catch (error) {
        if (error is ApiException && (error.statusCode == 401 || error.statusCode == 403)) rethrow;
        items = jsonDecode(prefs.getString(key) ?? '[]') as List;
      }
      final licenses = (actor['licensed_sectors'] as List? ?? []).map(FieldAccess.sector).whereType<String>().toSet();
      final projects = items.map((p) => Map<String, dynamic>.from(p as Map)).where((p) =>
        FieldAccess.projectSector(p) != null && (FieldAccess.role(actor['role']) == 'SUPER_ADMIN' || licenses.contains(FieldAccess.projectSector(p)))).toList();
      if (!mounted) return;
      setState(() {
        _user = user; _projects = projects; _loading = false;
        _selectedId = projects.any((p) => p['id'] == widget.projectId) ? widget.projectId : projects.length == 1 ? projects.first['id'] as String : null;
      });
    } catch (error) { if (mounted) setState(() { _loading = false; _error = error.toString(); }); }
  }
  @override
  Widget build(BuildContext context) {
    final matches = _projects.where((p) => p['id'] == _selectedId);
    final project = matches.isEmpty ? null : matches.first;
    final code = project == null ? null : FieldAccess.projectSector(project);
    if (_open && project != null && _user != null) {
      if (code == 'AGRICULTURE_LAND_USE') return SoilCollectionScreen(project: project, user: _user!);
      return ActivityFormScreen(projectId: _selectedId, initialActivityTypeId: FieldAccess.activityType(code), methodologyLock: project['methodology_code'] as String?);
    }
    return Scaffold(appBar: AppBar(title: const Text('Capture field data')), body: Padding(padding: const EdgeInsets.all(24), child: _loading ? const Center(child: CircularProgressIndicator()) : Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      if (_error != null) Text(_error!),
      if (_error == null) ...[
        const Text('Choose your assigned project.'), const SizedBox(height: 16),
        DropdownButtonFormField<String>(initialValue: _selectedId, decoration: const InputDecoration(labelText: 'Project'), items: _projects.map((p) => DropdownMenuItem(value: p['id'] as String, child: Text(p['name'] as String))).toList(), onChanged: (value) => setState(() => _selectedId = value)),
        if (_projects.isEmpty) const Padding(padding: EdgeInsets.only(top: 16), child: Text('No assigned projects with an authorized operating sector are available. Contact your project manager.')),
        const SizedBox(height: 24), FilledButton(onPressed: project == null ? null : () => setState(() => _open = true), child: const Text('Continue')),
      ],
    ])));
  }
}
