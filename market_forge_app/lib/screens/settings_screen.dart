import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/user_provider.dart';
import 'package:market_forge_app/models/user.dart';

/// Settings screen for account, subscription, and preferences
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: Consumer<UserProvider>(
        builder: (context, userProvider, child) {
          final user = userProvider.currentUser;

          if (user == null) {
            return const Center(
              child: Text('Not logged in'),
            );
          }

          return ListView(
            children: [
              // User profile section
              _buildProfileSection(context, user),
              
              const Divider(height: 1),
              
              // Subscription section
              _buildSubscriptionSection(context, user),
              
              const Divider(height: 1),
              
              // Marketplace connections section
              _buildMarketplaceSection(context),
              
              const Divider(height: 1),
              
              // Preferences section
              _buildPreferencesSection(context, userProvider),
              
              const Divider(height: 1),
              
              // About section
              _buildAboutSection(context),
              
              const Divider(height: 1),
              
              // Sign out button
              _buildSignOutSection(context, userProvider),
            ],
          );
        },
      ),
    );
  }

  Widget _buildProfileSection(BuildContext context, User user) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          CircleAvatar(
            radius: 40,
            backgroundColor: Colors.deepPurple,
            child: user.photoUrl != null
                ? ClipOval(
                    child: Image.network(
                      user.photoUrl!,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) {
                        return Text(
                          user.name?.substring(0, 1).toUpperCase() ?? 'U',
                          style: const TextStyle(fontSize: 32),
                        );
                      },
                    ),
                  )
                : Text(
                    user.name?.substring(0, 1).toUpperCase() ?? 'U',
                    style: const TextStyle(fontSize: 32),
                  ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  user.name ?? 'User',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  user.email,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.edit),
            onPressed: () {
              // TODO: Edit profile
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Edit profile coming soon')),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSubscriptionSection(BuildContext context, User user) {
    return ListTile(
      leading: const Icon(Icons.card_membership),
      title: const Text('Subscription'),
      subtitle: Text('${user.subscriptionTier.displayName} Plan'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () {
        _showSubscriptionDialog(context, user);
      },
    );
  }

  Widget _buildMarketplaceSection(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Marketplace Connections',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ),
        ListTile(
          leading: const Icon(Icons.facebook),
          title: const Text('Facebook Marketplace'),
          subtitle: const Text('Connected'),
          trailing: Switch(
            value: true,
            onChanged: (value) {
              // TODO: Toggle connection
            },
          ),
        ),
        ListTile(
          leading: const Icon(Icons.shopping_bag),
          title: const Text('eBay'),
          subtitle: const Text('Coming Soon'),
          trailing: const Icon(Icons.lock_outline),
          enabled: false,
        ),
        ListTile(
          leading: const Icon(Icons.list),
          title: const Text('Craigslist'),
          subtitle: const Text('Coming Soon'),
          trailing: const Icon(Icons.lock_outline),
          enabled: false,
        ),
      ],
    );
  }

  Widget _buildPreferencesSection(BuildContext context, UserProvider provider) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'Preferences',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ),
        SwitchListTile(
          secondary: const Icon(Icons.notifications),
          title: const Text('Notifications'),
          subtitle: const Text('Get notified about listing status'),
          value: provider.getPreference('notifications', defaultValue: true) as bool,
          onChanged: (value) {
            provider.savePreference('notifications', value);
          },
        ),
        SwitchListTile(
          secondary: const Icon(Icons.location_on),
          title: const Text('Auto-detect Location'),
          subtitle: const Text('Use your device location for listings'),
          value: provider.getPreference('autoLocation', defaultValue: true) as bool,
          onChanged: (value) {
            provider.savePreference('autoLocation', value);
          },
        ),
      ],
    );
  }

  Widget _buildAboutSection(BuildContext context) {
    return Column(
      children: [
        ListTile(
          leading: const Icon(Icons.info_outline),
          title: const Text('About MarketForge'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            _showAboutDialog(context);
          },
        ),
        ListTile(
          leading: const Icon(Icons.help_outline),
          title: const Text('Help & Support'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Help & Support coming soon')),
            );
          },
        ),
        ListTile(
          leading: const Icon(Icons.policy),
          title: const Text('Privacy Policy'),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Privacy Policy coming soon')),
            );
          },
        ),
      ],
    );
  }

  Widget _buildSignOutSection(BuildContext context, UserProvider provider) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: SizedBox(
        width: double.infinity,
        child: OutlinedButton(
          onPressed: () async {
            final confirmed = await _showSignOutConfirmation(context);
            if (confirmed == true) {
              await provider.signOut();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Signed out successfully')),
                );
              }
            }
          },
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
            foregroundColor: Colors.red,
            side: const BorderSide(color: Colors.red),
          ),
          child: const Text('Sign Out'),
        ),
      ),
    );
  }

  void _showSubscriptionDialog(BuildContext context, User user) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Subscription Plans'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: SubscriptionTier.values.map((tier) {
              final isCurrent = tier == user.subscriptionTier;
              return RadioListTile<SubscriptionTier>(
                value: tier,
                groupValue: user.subscriptionTier,
                title: Text(tier.displayName),
                subtitle: Text(
                  '${tier.maxListingsPerMonth == -1 ? 'Unlimited' : tier.maxListingsPerMonth} listings/month\n'
                  '${tier.maxMarketplaces} marketplaces',
                ),
                selected: isCurrent,
                onChanged: (value) {
                  if (value != null && !isCurrent) {
                    context.read<UserProvider>().updateSubscription(value);
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Upgraded to ${value.displayName}'),
                      ),
                    );
                  }
                },
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showAboutDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('About MarketForge'),
        content: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Version 1.0.0'),
            SizedBox(height: 16),
            Text(
              'MarketForge is the flagship product of EmpireBox, '
              'designed to help resellers list products to multiple '
              'marketplaces with ease.',
            ),
            SizedBox(height: 16),
            Text(
              '© 2026 EmpireBox. All rights reserved.',
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Future<bool?> _showSignOutConfirmation(BuildContext context) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
  }
}
