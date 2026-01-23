# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, Command, tools
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext
from markupsafe import Markup

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    channel_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp Conversation')],
        ondelete={'whatsapp': 'cascade'}
    )
    whatsapp_number = fields.Char(string="WhatsApp Number")
    wa_account_id = fields.Many2one('whatsapp_evaluation.account', string="WhatsApp Account")
    whatsapp_partner_id = fields.Many2one('res.partner', string="WhatsApp Partner")
    whatsapp_channel_valid_until = fields.Datetime(string="WhatsApp Channel Valid Until")

    def whatsapp_channel_join_and_pin(self):
        """ Adds the current partner as a member of self channel and pins them if not already pinned. """
        self.ensure_one()
        if self.channel_type != 'whatsapp':
            raise ValidationError(_('This join method is not possible for regular channels.'))

        self.check_access('write')
        current_partner = self.env.user.partner_id
        member = self.channel_member_ids.filtered(lambda m: m.partner_id == current_partner)
        if member:
            if not member.is_pinned:
                member.write({'unpin_dt': False})
        else:
            new_member = self.env['discuss.channel.member'].with_context(tools.clean_context(self.env.context)).sudo().create([{
                'partner_id': current_partner.id,
                'channel_id': self.id,
            }])
            message_body = Markup(f'<div class="o_mail_notification">{_("joined the channel")}</div>')
            new_member.channel_id.message_post(body=message_body, message_type="notification", subtype_xmlid="mail.mt_comment")
            try:
                 from odoo.addons.mail.tools.discuss import Store
            except ImportError:
                 from odoo.addons.mail.models.discuss.store import Store
            
            self._bus_send_store(Store(new_member).add(self, {"memberCount": self.member_count}))
        return Store(self).get_result()

    def _to_store(self, store):
        # Delayed import to avoid ImportError/NameError if paths differ in versions
        try:
            from odoo.addons.mail.tools.discuss import Store
        except ImportError:
            try:
                from odoo.addons.mail.models.discuss.store import Store
            except ImportError:
                # If Store is not found (e.g. Odoo 16 or different structure), we can't do much.
                # Assuming store object passed is valid (duck typing).
                # But we need Store class for Store.one() and Store(self)
                # Let's try to get it from the store object itself if possible? No.
                # We will just pass if checking class, but for Store(self) we need it.
                # Last resort fallback: Check odoo.addons.mail.models.discuss
                 from odoo.addons.mail.models.discuss import Store

        super()._to_store(store)
        for channel in self.filtered(lambda channel: channel.channel_type == "whatsapp"):
            store.add(channel, {
                "whatsapp_channel_valid_until": channel.whatsapp_channel_valid_until,
                "whatsapp_partner_id": Store.one(channel.whatsapp_partner_id, only_id=True),
            })

    def _types_allowing_seen_infos(self):
        return super()._types_allowing_seen_infos() + ["whatsapp"]

    
    @api.model
    def _get_whatsapp_channel(self, whatsapp_number, wa_account_id, create_if_not_found=False):
        """ Find or create a WhatsApp channel for the given number """
        domain = [
            ('channel_type', '=', 'whatsapp'),
            ('whatsapp_number', '=', whatsapp_number),
            ('wa_account_id', '=', wa_account_id.id)
        ]
        channel = self.sudo().search(domain, limit=1)
        
        if not channel and create_if_not_found:
            partner = self.env['res.partner'].sudo().search([('mobile', '=', whatsapp_number)], limit=1)
            name = whatsapp_number
            if partner:
                name = partner.name

            channel = self.sudo().create({
                'channel_type': 'whatsapp',
                'name': name,
                'whatsapp_number': whatsapp_number,
                'wa_account_id': wa_account_id.id,
            })
            if partner:
                 channel.add_members(partner.ids)
            
        # Ensure notify users are members (in case they were removed or channel existed before fix)
        if channel and wa_account_id.notify_user_ids:
            # We use add_members which handles duplication safely (only creates missing members)
            channel.add_members(wa_account_id.notify_user_ids.ids)
            
            # FORCE PIN for these users so it appears in specific sidebar category (or All)
            members = channel.channel_member_ids.filtered(
                lambda m: m.partner_id.id in wa_account_id.notify_user_ids.partner_id.ids
            )
            members.sudo().write({'unpin_dt': False, 'fold_state': 'open'})
            
        return channel

    def message_post(self, *args, **kwargs):
        """ Override to capture messages posted in WhatsApp channels """
        message = super().message_post(*args, **kwargs)
        
        # Check context for inbound flag (set in controller) to avoid infinite loop
        if self.channel_type == 'whatsapp' and not self.env.context.get('whatsapp_inbound_msg_uid'):
            # This is an outbound message from Odoo to WhatsApp
            self._create_whatsapp_message(message)
            
        return message

    def _create_whatsapp_message(self, message):
        """ Create linked WhatsApp message and send it """
        if not message.body and not message.attachment_ids:
            return

        # Prevent sending system notifications to WhatsApp (e.g. "User joined", "Subject changed")
        if message.message_type not in ('comment', 'whatsapp_message'):
             return

        body_text = html2plaintext(message.body)
        
        wa_msg = self.env['whatsapp_evaluation.message'].create({
            'body': body_text,
            'mobile_number': self.whatsapp_number,
            'wa_account_id': self.wa_account_id.id,
            'mail_message_id': message.id,
            'message_type': 'outbound',
            'state': 'outgoing',
            'attachment_ids': [Command.set(message.attachment_ids.ids)],
        })
        wa_msg._send_message()
