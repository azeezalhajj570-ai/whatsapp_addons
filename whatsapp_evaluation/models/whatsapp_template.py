# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval

class WhatsAppTemplate(models.Model):
    _name = 'whatsapp_evaluation.template'
    _description = 'WhatsApp Template'

    name = fields.Char(string="Name", required=True)
    body = fields.Text(string="Body", required=True, translate=True)
    model_id = fields.Many2one('ir.model', string="Applies to", required=True, ondelete='cascade')
    model = fields.Char(related='model_id.model', string="Related Document Model", store=True)
    variable_ids = fields.One2many('whatsapp_evaluation.template.variable', 'wa_template_id', string="Variables")

    Languages = [
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('fr', 'French'),
        ('es', 'Spanish'),
    ]

    header_type = fields.Selection([
        ('none', 'None'),
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('location', 'Location')], string="Header Type", default='none')
    header_text = fields.Char(string="Header Text")
    report_id = fields.Many2one(
        comodel_name='ir.actions.report', string="Report",
        domain="[('model', '=', model)]")
    header_attachment_ids = fields.Many2many(
        'ir.attachment', string="Template Static Header")
    lang_code = fields.Selection(string="Language", selection=Languages, default='en', required=True)

    def _generate_attachment_from_report(self, record=False):
        """Create attachment from report if relevant"""
        self.ensure_one()
        if record and self.header_type == 'document' and self.report_id:
            report_content, report_format = self.report_id._render_qweb_pdf(self.report_id, record.id)
            if self.report_id.print_report_name:
                report_name = safe_eval(self.report_id.print_report_name, {'object': record}) + '.' + report_format
            else:
                report_name = self.display_name + '.' + report_format
            return self.env['ir.attachment'].create({
                'name': report_name,
                'raw': report_content,
                'mimetype': 'application/pdf',
                'res_model': record._name,
                'res_id': record.id,
            })
        return self.env['ir.attachment']

    def _get_formatted_body(self, variable_values=None):
        self.ensure_one()
        variable_values = variable_values or {}
        header = ''
        if self.header_type == 'text' and self.header_text:
            header = f"*{self.header_text}*\n\n"
        
        body = self.body
        for var in self.variable_ids:
            if var.line_type == 'body':
                body = body.replace(var.name, variable_values.get(f'{var.line_type}-{var.name}', var.demo_value))
        
        return header + body

    @api.model
    def _can_use_whatsapp(self, model_name):
        """Check if the model can use WhatsApp (has templates or logic allowed)."""
        if model_name in ['res.partner', 'sale.order', 'account.move', 'account.payment', 'pos.order']:
            return True
        return len(self._find_default_for_model(model_name)) > 0

    @api.model
    def _find_default_for_model(self, model_name, lang_code=False):
        domain = [('model', '=', model_name)]
        if lang_code:
            domain.append(('lang_code', '=', lang_code))
        
        template = self.search(domain, limit=1)
        if not template and lang_code:
             # Fallback to English/Default if specific lang not found
             domain = [('model', '=', model_name)]
             template = self.search(domain, limit=1)
        return template
