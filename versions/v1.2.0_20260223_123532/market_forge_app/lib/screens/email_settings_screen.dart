import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class EmailSettingsScreen extends StatefulWidget {
  final String username;

  const EmailSettingsScreen({
    Key? key,
    required this.username,
  }) : super(key: key);

  @override
  State<EmailSettingsScreen> createState() => _EmailSettingsScreenState();
}

class _EmailSettingsScreenState extends State<EmailSettingsScreen> {
  bool _isForwardingEnabled = false;
  String _forwardingEmail = '';
  final TextEditingController _customDomainController = TextEditingController();

  @override
  void dispose() {
    _customDomainController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final emailAddress = '${widget.username}@marketforge.app';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Email Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildEmailAddressCard(emailAddress),
          const SizedBox(height: 16),
          _buildForwardingCard(),
          const SizedBox(height: 16),
          _buildCustomDomainCard(),
          const SizedBox(height: 16),
          _buildTestEmailButton(),
        ],
      ),
    );
  }

  Widget _buildEmailAddressCard(String emailAddress) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Your MarketForge Email',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Use this email address for all your marketplace communications.',
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      emailAddress,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.copy),
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: emailAddress));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Email address copied to clipboard'),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                    tooltip: 'Copy email address',
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildForwardingCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Email Forwarding',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Forward emails from your personal email to your MarketForge inbox.',
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              value: _isForwardingEnabled,
              onChanged: (value) {
                setState(() {
                  _isForwardingEnabled = value;
                });
              },
              title: const Text('Enable Forwarding'),
              contentPadding: EdgeInsets.zero,
            ),
            if (_isForwardingEnabled) ...[
              const SizedBox(height: 8),
              TextField(
                decoration: const InputDecoration(
                  labelText: 'Forwarding Email',
                  hintText: 'your-email@example.com',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.forward_to_inbox),
                ),
                keyboardType: TextInputType.emailAddress,
                onChanged: (value) {
                  _forwardingEmail = value;
                },
              ),
              const SizedBox(height: 8),
              Text(
                'Forward emails from this address to your MarketForge inbox',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.grey.shade600,
                    ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCustomDomainCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Custom Domain',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.amber,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'PRO',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Use your own domain for email (e.g., username@yourdomain.com)',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _customDomainController,
              decoration: const InputDecoration(
                labelText: 'Custom Domain',
                hintText: 'yourdomain.com',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.domain),
              ),
              enabled: false, // Disabled for free tier
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _showUpgradeDialog,
                icon: const Icon(Icons.workspace_premium),
                label: const Text('Upgrade to Pro'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amber,
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTestEmailButton() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Test Your Email',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Send a test email to verify your setup is working correctly.',
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _sendTestEmail,
                icon: const Icon(Icons.send),
                label: const Text('Send Test Email'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _sendTestEmail() {
    // TODO: Implement test email sending
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Test email sent to ${widget.username}@marketforge.app',
        ),
        backgroundColor: Colors.green,
      ),
    );
  }

  void _showUpgradeDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Upgrade to Pro'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Unlock premium features with Pro:',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            _buildFeatureItem('Custom domain email'),
            _buildFeatureItem('Priority support'),
            _buildFeatureItem('Advanced AI features'),
            _buildFeatureItem('Unlimited message history'),
            const SizedBox(height: 16),
            const Text(
              '\$19.99/month',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Colors.amber,
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Maybe Later'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Upgrade feature coming soon!'),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.amber,
              foregroundColor: Colors.black,
            ),
            child: const Text('Upgrade Now'),
          ),
        ],
      ),
    );
  }

  Widget _buildFeatureItem(String feature) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          const Icon(Icons.check_circle, color: Colors.green, size: 20),
          const SizedBox(width: 8),
          Text(feature),
        ],
      ),
    );
  }
}
