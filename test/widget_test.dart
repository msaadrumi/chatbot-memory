import 'package:flutter_test/flutter_test.dart';
import 'package:chatbot_app/main.dart';

void main() {
  testWidgets('App launches with chat screen', (WidgetTester tester) async {
    await tester.pumpWidget(const ChatbotApp());
    expect(find.text('Start a conversation'), findsOneWidget);
  });
}
