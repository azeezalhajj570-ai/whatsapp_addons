# Evolution API Instance Manager - Setup Guide

## Requirements
- Odoo 18.0
- Reachable Evolution API server (v2.x)
- Server API key for Evolution API

## Configuration
1. Install the module `evolution_instance_manager`.
2. Go to **Settings > General Settings**.
3. In **Evolution API** section, set:
   - **Evolution Base URL** (example: `https://api.example.com`)
   - **Evolution Server API Key**
4. Save settings.

## Usage
1. Open **Evolution API > Instances**.
2. Create a new instance account.
3. Click **Create Instance in Evolution**.
4. Click **Get QR Code** and scan it with WhatsApp.
5. Use **Refresh Status** to sync connection state.
6. Use **Delete Instance** to remove it remotely and clear local identifiers.

## Notes
- Instance names are unique per company.
- Access is restricted by multi-company record rules.
- A cron job periodically syncs status for active records.
