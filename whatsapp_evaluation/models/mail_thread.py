# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _thread_to_store(self, store, /, *, request_list=None, **kwargs):
        super()._thread_to_store(store, request_list=request_list, **kwargs)
        if request_list:
            store.add(
                self,
                {"canSendWhatsapp": self.env["whatsapp_evaluation.template"]._can_use_whatsapp(self._name)},
                as_thread=True,
            )
