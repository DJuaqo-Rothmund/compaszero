import 'package:flet/flet.dart';
import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_recognition_result.dart';
import 'package:speech_to_text/speech_to_text.dart';

class SpeechService extends FletService {
  SpeechService({required super.control});

  final SpeechToText _speech = SpeechToText();
  bool _ready = false;

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_invokeMethod);
  }

  void _onResult(SpeechRecognitionResult r) {
    control.triggerEvent(
        "result", {"text": r.recognizedWords, "final": r.finalResult});
  }

  void _onStatus(String status) {
    control.triggerEvent("status", {"status": status});
  }

  void _onError(SpeechRecognitionError e) {
    control.triggerEvent(
        "error", {"message": e.errorMsg, "permanent": e.permanent});
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("SpeechToText.$name($args)");
    switch (name) {
      case "initialize":
        if (!_ready) {
          _ready = await _speech.initialize(
              onStatus: _onStatus, onError: _onError, debugLogging: false);
        }
        return _ready;
      case "listen":
        if (!_ready) {
          _ready = await _speech.initialize(
              onStatus: _onStatus, onError: _onError);
        }
        if (!_ready) return false;
        await _speech.listen(
          onResult: _onResult,
          localeId: args["locale"],
          pauseFor: Duration(seconds: (args["pause_for"] ?? 4) as int),
          listenFor: Duration(seconds: (args["listen_for"] ?? 120) as int),
          listenOptions: SpeechListenOptions(
            partialResults: true,
            listenMode: ListenMode.dictation,
            cancelOnError: false,
          ),
        );
        return true;
      case "stop":
        await _speech.stop();
        return null;
      case "cancel":
        await _speech.cancel();
        return null;
      case "locales":
        final l = await _speech.locales();
        return l.map((e) => e.localeId).toList();
      default:
        throw Exception("Unknown SpeechToText method: $name");
    }
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    _speech.cancel();
    super.dispose();
  }
}
