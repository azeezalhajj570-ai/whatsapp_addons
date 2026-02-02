import json
import logging
from odoo import models, api, _

from .extended_whatsapp_api import ExtendedWhatsAppApi

_logger = logging.getLogger(__name__)

class WhatsAppProjectAIOrchestrator(models.AbstractModel):
    _name = 'whatsapp.project.ai.orchestrator'
    _description = 'WhatsApp AI Project Orchestrator'

    def process_incoming_message(self, message):
        """Main entry point for AI processing"""
        if message.is_ai_processed:
            _logger.info(f"AI Orchestrator: Message {message.id} already processed. Skipping.")
            return

        _logger.info(f"AI Orchestrator: Processing message {message.id}")
        
        agent = self.env.ref('whatsapp_project_ai.agent_whatsapp_pm', raise_if_not_found=False)
        if not agent:
            _logger.warning("AI Orchestrator: Agent 'agent_whatsapp_pm' not found.")
            return

        # 1. Build Service Catalog
        # Fetch services (Products)
        # We assume 'service' type and 'sale_ok'
        products = self.env['product.template'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        
        # Build lightweight catalog
        # Use product.tags (product.tag) for keywords
        service_catalog = []
        for p in products:
            service_catalog.append({
                "id": p.id,
                "name": p.name,
                "tags": [t.name for t in p.product_tag_ids], # product_tag_ids (product.template)
                "category": p.categ_id.complete_name
            })
            
        catalog_json = json.dumps(service_catalog, indent=2)

        # 2. Call AI
        try:
            prompt = (
                f"Message: {message.body}\n"
                f"Sender Phone: {message.mobile_number}\n\n"
                f"### SERVICE CATALOG ###\n"
                f"{catalog_json}"
            )
            
            responses = agent.get_direct_response(prompt=prompt)
            if not responses:
                _logger.warning("AI Orchestrator: No response from AI Agent.")
                return
            
            ai_output_str = responses[0]
            
            if "```json" in ai_output_str:
                ai_output_str = ai_output_str.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_output_str:
                ai_output_str = ai_output_str.split("```")[1].split("```")[0].strip()

            ai_data = json.loads(ai_output_str)
            
            # 3. Update Message Record
            vals = {
                'ai_intent': ai_data.get('intent'),
                'ai_confidence': ai_data.get('confidence', 0.0),
                'ai_rationale': ai_data.get('rationale'),
                'is_ai_processed': True,
            }
            message.write(vals)

            if vals['ai_confidence'] < 0.60:
                _logger.info(f"AI Orchestrator: Confidence {vals['ai_confidence']} too low. Skipping automation.")
                return

            self._execute_decision(message, ai_data)
            
        except Exception as e:
            error_msg = str(e)
            _logger.exception("AI Orchestrator: Error processing message.")
            
            # Notify Admin for Critical AI Failures
            if "Quota exceeded" in error_msg or "429" in error_msg or "insufficient_quota" in error_msg:
                try:
                    admin_user = self.env.ref('base.user_admin')
                    message.activity_schedule(
                        'mail.mail_activity_data_todo',
                        user_id=admin_user.id,
                        summary=f"AI Quota Exceeded: {message.mobile_number}",
                        note=f"The AI processing failed due to a quota/rate-limit error. Please check your AI Provider billing/plans.<br/>Error: {error_msg}"
                    )
                except Exception as ex:
                    _logger.error(f"Failed to create admin activity: {ex}")

            message.write({'is_ai_processed': True, 'ai_rationale': f"Error: {error_msg}"})

    def _execute_decision(self, message, ai_data):
        intent = ai_data.get('intent')
        service_id = ai_data.get('service_id')
        reply_text = ai_data.get('suggested_reply')

        redirect_record = None
        
        product = None
        if service_id:
            product = self.env['product.template'].browse(service_id)

        # Decision Logic based on Product Category (if service found) OR Intent
        
        if intent == 'new_service' and product:
            # Check Category for Routing
            category_path = product.categ_id.complete_name or ""
            
            if 'Project' in category_path:
                 redirect_record = self._create_project(message, product, ai_data)
            elif 'Support' in category_path:
                 redirect_record = self._create_support_task(message, product, ai_data)
            else:
                 # Default fallback if category doesn't specify
                 redirect_record = self._create_lead_only(message, product, ai_data)

        elif intent == 'support':
             # Even if no specific product, handle generic support
             redirect_record = self._create_support_task(message, product, ai_data) # product might be None

        elif intent == 'inquiry':
             redirect_record = self._create_lead_only(message, product, ai_data)
        
        if redirect_record:
            try:
                message.write({
                    'linked_model': redirect_record._name,
                    'linked_res_id': redirect_record.id,
                })
            except Exception:
                pass

        if reply_text:
            self._send_auto_reply(message, reply_text)

    def _create_project(self, message, product, ai_data):
        # Create Lead first (always good practice)
        Lead = self.env['crm.lead']
        lead = Lead.create({
            'name': f"WA Project: {product.name}",
            'partner_id': message.partner_id.id if message.partner_id else False,
            'description': f"Service: {product.name}\nMsg: {message.body}\nRationale: {ai_data.get('rationale')}",
        })
        
        # Create Project
        Project = self.env['project.project']
        project = Project.create({
            'name': f"{message.mobile_number} - {product.name}",
            'partner_id': message.partner_id.id if message.partner_id else False,
            'description': lead.description,
            'tag_ids': [(6, 0, product.product_tag_ids.ids)] # Copy tags
        })
        return project

    def _create_support_task(self, message, product, ai_data):
        Project = self.env['project.project']
        # Find generic support project or specific logic
        support_project = Project.search([('name', 'ilike', 'Support')], limit=1)
        if not support_project:
            support_project = Project.create({'name': 'General Support'})

        Task = self.env['project.task']
        task_name = f"Support: {product.name}" if product else f"Support: {message.body[:30]}"
        
        task = Task.create({
            'name': task_name,
            'project_id': support_project.id,
            'partner_id': message.partner_id.id if message.partner_id else False,
            'description': f"From: {message.mobile_number}\n\n{message.body}",
        })
        return task

    def _create_lead_only(self, message, product, ai_data):
        Lead = self.env['crm.lead']
        name = f"WA Inquiry: {product.name}" if product else f"WA Inquiry: {message.body[:30]}"
        lead = Lead.create({
            'name': name,
            'partner_id': message.partner_id.id if message.partner_id else False,
            'description': message.body,
        })
        return lead

    def _send_auto_reply(self, original_message, reply_text):
        try:
            # 1. Instantiate Extended API
            account = original_message.wa_account_id
            api = ExtendedWhatsAppApi(
                base_url=account.api_url,
                instance_name=account.instance_name,
                api_key=account.api_key,
                instance_token=account.instance_token
            )
            
            # 2. Send with Delay (15s)
            # This bypasses the model's standard _send_message but ensures we use our specific delay logic
            response = api._send_whatsapp(original_message.mobile_number, reply_text, delay=15000)
            
            msg_uid = False
            if isinstance(response, dict):
                if 'key' in response:
                    msg_uid = response['key'].get('id')
                elif 'id' in response:
                    msg_uid = response['id']

            # 3. Log the message in Odoo
            self.env['whatsapp_evaluation.message'].create({
                'body': reply_text,
                'mobile_number': original_message.mobile_number,
                'wa_account_id': account.id,
                'message_type': 'outbound',
                'state': 'sent',
                'msg_uid': msg_uid,
            })
            
            _logger.info(f"AI Orchestrator: Auto-reply sent to {original_message.mobile_number} (Delayed 15s)")
        except Exception as e:
            _logger.exception(f"AI Orchestrator: Failed to send auto-reply: {e}")
