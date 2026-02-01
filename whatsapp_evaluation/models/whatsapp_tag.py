from odoo import models, fields

class WhatsAppEvaluationTag(models.Model):
    _name = 'whatsapp_evaluation.tag'
    _description = 'WhatsApp Message Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color')
