import 'package:uni_links/uni_links.dart';
import 'dart:async';

class DeepLinkService {
  StreamSubscription? _sub;
  
  void init(Function(Uri) onDeepLink) {
    // Handle deep links when app is already running
    _sub = linkStream.listen((String? link) {
      if (link != null) {
        final uri = Uri.parse(link);
        onDeepLink(uri);
      }
    }, onError: (err) {
      print('Deep link error: $err');
    });
    
    // Handle deep links that launched the app
    getInitialLink().then((String? link) {
      if (link != null) {
        final uri = Uri.parse(link);
        onDeepLink(uri);
      }
    });
  }
  
  void handleDeepLink(Uri uri, Function(String licenseKey) onSetupLink) {
    // Handle empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX
    if (uri.host == 'empirebox.store' || uri.host == 'www.empirebox.store') {
      final pathSegments = uri.pathSegments;
      
      if (pathSegments.isNotEmpty && pathSegments[0] == 'setup') {
        if (pathSegments.length > 1) {
          final licenseKey = pathSegments[1];
          onSetupLink(licenseKey);
        }
      }
    }
  }
  
  void dispose() {
    _sub?.cancel();
  }
}
