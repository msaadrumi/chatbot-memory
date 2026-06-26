import 'dart:convert';
import 'package:http/http.dart' as http;

class ChatService {
  final String baseUrl;
  String? _sessionId;

  ChatService(this.baseUrl);

  String? get sessionId => _sessionId;

  Future<Map<String, dynamic>> sendMessage(String message) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/chat'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'message': message,
        'session_id': _sessionId,
      }),
    );

    if (res.statusCode != 200) {
      final body = jsonDecode(res.body);
      throw Exception(body['detail'] ?? 'Error ${res.statusCode}');
    }

    final data = jsonDecode(res.body) as Map<String, dynamic>;
    _sessionId = data['session_id'] as String;
    return data;
  }

  Future<void> resetSession() async {
    if (_sessionId == null) return;
    await http.post(
      Uri.parse('$baseUrl/api/reset'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'session_id': _sessionId}),
    );
    _sessionId = null;
  }

  Future<Map<String, dynamic>?> getStats() async {
    if (_sessionId == null) return null;
    final res = await http.get(
      Uri.parse('$baseUrl/api/stats/$_sessionId'),
    );
    if (res.statusCode != 200) return null;
    return jsonDecode(res.body) as Map<String, dynamic>;
  }
}
