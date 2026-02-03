import json
import logging
from odoo import models, api, fields, _

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
        products = self.env['product.template'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        
        # Build lightweight service catalog
        service_catalog = []
        for p in products:
            service_catalog.append({
                "id": p.id,
                "name": p.name,
                "tags": [t.name for t in p.product_tag_ids],
                "category": p.categ_id.complete_name
            })

        # Fetch Project Tags for Intent Classification
        project_tags = self.env['project.tags'].search([])
        tag_list = [t.name for t in project_tags]

        catalog_json = json.dumps({
            "services": service_catalog,
            "available_intents": tag_list
        }, indent=2)

        # 2. Call AI
        try:
            prompt = (
                f"Message: {message.body}\n"
                f"Sender Phone: {message.mobile_number}\n\n"
                f"### DATA CATALOG ###\n"
                f"{catalog_json}\n\n"
                f"Instructions:\n"
                f"1. Analyze the message.\n"
                f"2. Select the most appropriate 'intent_tag' from 'available_intents'.\n"
                f"3. If clear match to a service, return 'service_id'.\n"
                f"4. Output JSON: {{ 'intent_tag': '...', 'service_id': ... }}"
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
            intent_tag_name = ai_data.get('intent_tag')
            
            # Apply Tags
            tag_ids = []
            if intent_tag_name:
                # Find or Create PROJECT Tag
                # We use project.tags directly now
                p_tag = self.env['project.tags'].search([('name', '=', intent_tag_name)], limit=1)
                if not p_tag:
                    p_tag = self.env['project.tags'].create({'name': intent_tag_name})
                tag_ids.append(p_tag.id)

            # 3. Update Message Record
            vals = {
                # 'ai_intent': intent_tag_name, # Removed to avoid Selection Error, relies on Tags now
                'ai_confidence': ai_data.get('confidence', 0.0),
                'ai_rationale': ai_data.get('rationale'),
                'is_ai_processed': True,
                'tag_ids': [(4, t_id) for t_id in tag_ids]
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
        
        related_record = None
        product = None
        if service_id:
            product = self.env['product.template'].browse(service_id)

        # --- DECISION LOGIC ---
        if intent in ['new_service_request', 'pricing_question']:
            related_record = self.action_create_lead(message, product, ai_data)
        
        elif intent == 'confirmed_work':
            related_record = self.action_create_project(message, product, ai_data)
            
        elif intent in ['support_issue', 'revision']:
            related_record = self.action_create_task(message, product, ai_data)

        # Update Link
        if related_record:
            try:
                message.write({
                    'linked_model': related_record._name,
                    'linked_res_id': related_record.id,
                })
            except Exception:
                pass

        if reply_text:
            self.action_reply_to_user(message, reply_text)

    def action_create_lead(self, message, product=None, ai_data=None):
        """Public action to create a lead from a message"""
        if not ai_data: ai_data = {}
        Lead = self.env['crm.lead']
        
        name = f"Inquiry: {product.name}" if product else f"Inquiry: {message.body[:30]}"
        
        # Map Project Tags -> CRM Tags (by Name)
        crm_tag_ids = []
        for p_tag in message.tag_ids:
            c_tag = self.env['crm.tag'].search([('name', '=', p_tag.name)], limit=1)
            if not c_tag:
                c_tag = self.env['crm.tag'].create({'name': p_tag.name})
            crm_tag_ids.append(c_tag.id)

        # Salesperson Logic
        salesperson_id = message.partner_id.user_id.id or self.env.ref('base.user_admin').id

        lead = Lead.create({
            'name': name,
            'partner_id': message.partner_id.id if message.partner_id else False,
            'contact_name': message.partner_id.name or message.mobile_number, 
            'description': f"Msg: {message.body}\nRationale: {ai_data.get('rationale', 'Manual Action')}",
            'type': 'lead',
            'tag_ids': [(6, 0, crm_tag_ids)],
            'user_id': salesperson_id,
            'priority': ai_data.get('priority', '1'),
            'expected_revenue': ai_data.get('expected_revenue', 0.0),
            'email_from': ai_data.get('customer_email') or message.partner_id.email
        })
        _logger.info(f"AI Orchestrator: Created Lead {lead.id} for message {message.id}")
        return lead

    def action_create_project(self, message, product=None, ai_data=None):
        """Public action to create a project (converting lead if exists)"""
        if not ai_data: ai_data = {}
        
        # 1. Find recent open lead
        Lead = self.env['crm.lead']
        domain = [('partner_id', '=', message.partner_id.id), ('type', '=', 'lead'), ('probability', '<', 100)]
        lead = Lead.search(domain, order='create_date desc', limit=1)
        
        if not lead:
            # Fallback: Create new lead first if none exists to convert
            lead = self.action_create_lead(message, product, ai_data)
            
        # 2. Mark Lead as Won (Workflow)
        lead.action_set_won()
        
        # 3. Create Project
        Project = self.env['project.project']
        project_name = f"Project: {product.name}" if product else f"Project: {lead.name}"
        
        project = Project.create({
            'name': project_name,
            'partner_id': message.partner_id.id,
            'description': f"Converted from Lead: {lead.name}\n\nLatest Msg: {message.body}",
            'tag_ids': [(6, 0, message.tag_ids.ids)]
        })
        _logger.info(f"AI Orchestrator: Created Project {project.id} from Lead {lead.id}")
        return project

    def action_create_task(self, message, product=None, ai_data=None):
        """Public action to create a task"""
        if not ai_data: ai_data = {}
        
        # Find active project for this user
        Project = self.env['project.project']
        # Look for recent project
        project = Project.search([('partner_id', '=', message.partner_id.id)], order='create_date desc', limit=1)
        
        if not project:
            # Fallback: Support Project
            project = Project.search([('name', 'ilike', 'Support')], limit=1)
            if not project:
                project = Project.create({'name': 'General Support'})

        Task = self.env['project.task']
        task_name = f"Task: {product.name}" if product else f"Request: {message.body[:30]}"
        
        # 1. Deadline Calculation
        from datetime import timedelta
        deadline_days = int(ai_data.get('deadline_days', 3))
        date_deadline = fields.Date.today() + timedelta(days=deadline_days)
        
        # 2. Assignee Logic (Project Manager -> Salesperson -> Admin)
        public_user_id = self.env.ref('base.public_user').id
        possible_assignees = [project.user_id, message.partner_id.user_id]
        
        assignee_id = self.env.ref('base.user_admin').id # Default fallback
        for user in possible_assignees:
            if user and user.id != public_user_id:
                assignee_id = user.id
                break

        # 3. Find 'To Do' Stage
        stage = self.env['project.task.type'].search([
            ('name', 'in', ['To Do', 'New']),
            ('project_ids', 'in', [project.id])
        ], limit=1)
        
        # Fallback to generic 'To Do' if not specific to this project
        if not stage:
             stage = self.env['project.task.type'].search([('name', '=', 'To Do')], limit=1)

        task = Task.create({
            'name': task_name,
            'project_id': project.id,
            'partner_id': message.partner_id.id,
            'description': f"Msg: {message.body}\nRationale: {ai_data.get('rationale', 'Manual Action')}",
            'tag_ids': [(6, 0, message.tag_ids.ids)],
            'user_ids': [(4, assignee_id)],
            'date_deadline': date_deadline,
            'stage_id': stage.id if stage else False
        })
        _logger.info(f"AI Orchestrator: Created Task {task.id}")
        return task

    def action_reply_to_user(self, message, reply_text):
        """Public action to send a reply"""
        try:
            # 1. Instantiate Extended API
            account = message.wa_account_id
            api = ExtendedWhatsAppApi(
                base_url=account.base_url,
                instance_name=account.instance_name,
                api_key=account.api_key,
                instance_token=account.instance_token
            )
            
            # 2. Send with Delay (15s)
            response = api._send_whatsapp(message.mobile_number, reply_text, delay=15000)
            
            msg_uid = False
            if isinstance(response, dict):
                if 'key' in response:
                    msg_uid = response['key'].get('id')
                elif 'id' in response:
                    msg_uid = response['id']

            # 3. Log the message in Odoo
            self.env['whatsapp_evaluation.message'].create({
                'body': reply_text,
                'mobile_number': message.mobile_number,
                'wa_account_id': account.id,
                'message_type': 'outbound',
                'state': 'sent',
                'msg_uid': msg_uid,
            })
            
            _logger.info(f"AI Orchestrator: Auto-reply sent to {message.mobile_number}")
        except Exception as e:
            _logger.exception(f"AI Orchestrator: Failed to send auto-reply: {e}")

    def action_follow_up_project(self, message):
        """Public action to follow up on the user's latest project"""
        # Find latest project
        Project = self.env['project.project']
        project = Project.search([('partner_id', '=', message.partner_id.id)], order='create_date desc', limit=1)
        
        if not project:
            # If no project, maybe just reply saying no project found? Or treat as new lead?
            # For now, we'll log a warning and maybe send a generic reply
            self.action_reply_to_user(message, "I couldn't find an ongoing project to follow up on. How can I help you today?")
            return

        # Create a status report or check status
        # This is a good place to use AI to summarize, but for this specific action, 
        # let's just create a generic follow-up note or task
        
        # Logic: Check if there are open tasks
        open_tasks = self.env['project.task'].search_count([
            ('project_id', '=', project.id),
            ('stage_id.is_closed', '=', False)
        ])
        
        reply = f"Regarding project '{project.name}': You have {open_tasks} open tasks."
        self.action_reply_to_user(message, reply)
