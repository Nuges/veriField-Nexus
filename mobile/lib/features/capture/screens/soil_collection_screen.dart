import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';
import '../../../services/api_service.dart';
import '../../../services/location_service.dart';
import '../../../services/sync_service.dart';
import '../../../core/utils/field_access.dart';

class SoilCollectionScreen extends StatefulWidget {
  final Map<String, dynamic> project;
  final Map<String, dynamic> user;
  const SoilCollectionScreen({super.key, required this.project, required this.user});
  @override
  State<SoilCollectionScreen> createState() => _SoilCollectionScreenState();
}
class _SoilCollectionScreenState extends State<SoilCollectionScreen> {
  final _sample = TextEditingController();
  final _depth = TextEditingController();
  final _notes = TextEditingController();
  final _deviation = TextEditingController();
  Map<String, double>? _location;
  List<Map<String, dynamic>> _queue = [];
  String? _message;
  bool _busy = false;
  String get _queueKey => 'soil_collections:${widget.user['organization_id']}:${widget.user['id']}';
  @override
  void initState() { super.initState(); _loadQueue(); }
  Future<void> _loadQueue() async {
    final prefs = await SharedPreferences.getInstance();
    final records = jsonDecode(prefs.getString(_queueKey) ?? '[]') as List;
    if (mounted) setState(() => _queue = records.map((r) => Map<String, dynamic>.from(r as Map)).toList());
  }
  Future<void> _saveQueue(List<Map<String, dynamic>> records) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_queueKey, jsonEncode(records));
    if (mounted) setState(() => _queue = records);
  }
  Future<void> _locate() async {
    final result = await LocationService.getLocationResult();
    if (mounted) setState(() { _location = result.data; _message = result.errorReason; });
  }
  Future<void> _send(Map<String, dynamic> record) async {
    final user = await ApiService.get('/auth/me');
    if (user['id'] != widget.user['id'] || !FieldAccess.canCapture(user['role'])) throw Exception('Sign in with the account that captured this record.');
    await ApiService.post('/agriculture/projects/${record['project_id']}/physical-samples/${record['sample_id']}/collection', body: Map<String, dynamic>.from(record['payload'] as Map));
  }
  Future<void> _submit() async {
    final depth = double.tryParse(_depth.text);
    if (_location == null || depth == null || !depth.isFinite || depth <= 0 || !RegExp(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$').hasMatch(_sample.text.trim())) {
      setState(() => _message = 'Provide the assigned sample UUID, a positive depth and the actual GPS location.'); return;
    }
    setState(() { _busy = true; _message = null; });
    final record = <String, dynamic>{'project_id': widget.project['id'], 'sample_id': _sample.text.trim(), 'payload': {
      'actual_lat': _location!['latitude'], 'actual_lon': _location!['longitude'], 'actual_depth_from_cm': 0, 'actual_depth_to_cm': depth,
      'collector_name': widget.user['full_name'], 'collection_timestamp': DateTime.now().toUtc().toIso8601String(),
      'sample_condition': 'GOOD', 'notes': _notes.text, 'deviation_reason': _deviation.text.isEmpty ? null : _deviation.text,
      'idempotency_key': const Uuid().v4(), 'device_metadata': {'gps_accuracy_meters': _location!['accuracy']},
    }};
    try {
      if (await SyncService.isOnline()) { await _send(record); if (mounted) setState(() => _message = 'Collection recorded.'); }
      else { await _saveQueue([..._queue, record]); if (mounted) setState(() => _message = 'Saved offline. Sync when connected.'); }
    } catch (error) { if (mounted) setState(() => _message = error.toString()); }
    finally { if (mounted) setState(() => _busy = false); }
  }
  Future<void> _sync() async {
    setState(() => _busy = true);
    try {
      while (_queue.isNotEmpty) { await _send(_queue.first); await _saveQueue(_queue.sublist(1)); }
      if (mounted) setState(() => _message = 'Saved collections submitted.');
    } catch (error) { if (mounted) setState(() => _message = error.toString()); }
    finally { if (mounted) setState(() => _busy = false); }
  }
  @override
  void dispose() { _sample.dispose(); _depth.dispose(); _notes.dispose(); _deviation.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Soil sample collection')), body: ListView(padding: const EdgeInsets.all(24), children: [
    Text(widget.project['name'] as String), const SizedBox(height: 16),
    if (_queue.isNotEmpty) TextButton(onPressed: _busy ? null : _sync, child: Text('Sync ${_queue.length} saved collections')),
    TextField(controller: _sample, decoration: const InputDecoration(labelText: 'Physical sample ID')),
    TextField(controller: _depth, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Depth (cm)')),
    TextField(controller: _deviation, decoration: const InputDecoration(labelText: 'Location deviation reason')),
    TextField(controller: _notes, decoration: const InputDecoration(labelText: 'Notes')),
    const SizedBox(height: 16), TextButton(onPressed: _busy ? null : _locate, child: const Text('Use current location')),
    if (_location != null) Text('${_location!['latitude']}, ${_location!['longitude']}'),
    if (_message != null) Padding(padding: const EdgeInsets.symmetric(vertical: 16), child: Text(_message!)),
    FilledButton(onPressed: _busy ? null : _submit, child: Text(_busy ? 'Saving…' : 'Record collection')),
  ]));
}
