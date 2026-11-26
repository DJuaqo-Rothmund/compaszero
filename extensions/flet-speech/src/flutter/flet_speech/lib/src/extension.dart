import 'package:flet/flet.dart';

import 'speech.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "SpeechToText":
        return SpeechService(control: control);
      default:
        return null;
    }
  }
}
