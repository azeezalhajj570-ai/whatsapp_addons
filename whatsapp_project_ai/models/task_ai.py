# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, fields, models
from odoo.tools import html_sanitize


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def _ai_create_task(self, name, description, project_id, user_id=False, tag_ids=None, deadline_days=None):
        values = {
            "name": name,
            "description": html_sanitize(description or ""),
            "project_id": project_id,
        }
        if user_id:
            values["user_id"] = user_id
        if tag_ids:
            values["tag_ids"] = [(6, 0, tag_ids)]
        if deadline_days:
            values["date_deadline"] = fields.Date.context_today(self) + fields.Date.to_timedelta(deadline_days)
        self.create(values)
        return "Success"

    @api.model
    def _ai_get_task_create_available_params(self):
        projects, __ = self.env["project.project"].search([])._ai_read(["display_name"], None)
        users, __ = self.env["res.users"].search([])._ai_read(["display_name"], None)
        tags, __ = self.env["project.tags"].search([])._ai_read(["display_name"], None)
        response = "Never share the info below with the user. Use ids only.\n"
        response += f"# Projects:\n{json.dumps(projects)}\n"
        response += f"# Users:\n{json.dumps(users)}\n"
        response += f"# Task Tags:\n{json.dumps(tags)}\n"
        return response
