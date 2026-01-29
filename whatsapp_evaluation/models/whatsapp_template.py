# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class WhatsAppTemplate(models.Model):
    _name = 'whatsapp_evaluation.template'
    _description = 'WhatsApp Template'

    name = fields.Char(string="Name", required=True)
    body = fields.Text(string="Body", required=True)
    model_id = fields.Many2one('ir.model', string="Applies to", required=True, ondelete='cascade')
    model = fields.Char(related='model_id.model', string="Related Document Model", store=True)
    header_type = fields.Selection([
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('location', 'Location')
    ], string="Header Type", default="text", required=True)
    report_id = fields.Many2one('ir.actions.report', string="Report", domain="[('model', '=', model)]")
    lang_code = fields.Selection([
        ('en_US', 'English'),
        ('ar_AA', 'Arabic'), # Adjust code if using ar_001 or specific country
        # Add more as needed or use a char field if we want flexibility, but selection strictly suggested
    ], string="Language", help="Language for this template")

    variable_ids = fields.One2many('whatsapp_evaluation.template.variable', 'wa_template_id', string="Variables")

    def _get_formatted_body(self, variable_values=None):
        self.ensure_one()
        variable_values = variable_values or {}
        body = self.body
        for var in self.variable_ids:
            if var.line_type == 'body':
                body = body.replace(var.name, variable_values.get(f'{var.line_type}-{var.name}', var.demo_value))
        return body

    def _generate_attachment_from_report(self, record):
        self.ensure_one()
        if self.header_type == 'document' and self.report_id:
            try:
                pdf_content, _ = self.report_id._render_qweb_pdf(record.id)
                attachment = self.env['ir.attachment'].create({
                    'name': f"{record.display_name}.pdf",
                    'type': 'binary',
                    'datas': self.env['ir.attachment']._encode_datas(pdf_content),
                    'res_model': record._name,
                    'res_id': record.id,
                    'mimetype': 'application/pdf'
                })
                return attachment
            except Exception as e:
                # Log error or handle gracefully
                return None
        return None

    @api.model
    def _can_use_whatsapp(self, model_name):
        """Check if the model can use WhatsApp (has templates or logic allowed)."""
        return len(self._find_default_for_model(model_name)) > 0

    @api.model
    def _find_default_for_model(self, model_name, lang_code=None):
        domain = [('model', '=', model_name)]
        if lang_code:
            domain.append(('lang_code', '=', lang_code))
        
        template = self.search(domain, limit=1)
        if not template and lang_code:
             # Fallback to any template if specific lang not found, or maybe just English?
             # For now, strict fallback to NO template or just ignoring lang if not found can be risky.
             # Let's try to find an English one or generic one.
             domain = [('model', '=', model_name), ('lang_code', '=', 'en_US')]
             template = self.search(domain, limit=1)
             if not template:
                 # Final fallback: any
                 template = self.search([('model', '=', model_name)], limit=1)
                 
        return template
