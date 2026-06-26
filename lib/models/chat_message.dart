class ChatMessage {
  final String role;
  final String content;

  ChatMessage({required this.role, required this.content});

  bool get isUser => role == 'user';
}
