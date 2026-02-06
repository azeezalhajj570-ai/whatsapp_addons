# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, models
from odoo.tools import html_sanitize


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model
    def _ai_create_project(self, name, description, user_id=False, partner_id=False, tag_ids=None):
        values = {
            "name": name,
            "description": html_sanitize(description or ""),
        }
        if user_id:
            values["user_id"] = user_id
        if partner_id:
            values["partner_id"] = partner_id
        if tag_ids:
            values["tag_ids"] = [(6, 0, tag_ids)]
        self.create(values)
        return "Success"

    @api.model
    def _ai_get_project_create_available_params(self):
        users, __ = self.env["res.users"].search([])._ai_read(["display_name"], None)
        tags, __ = self.env["project.tags"].search([])._ai_read(["display_name"], None)
        response = "Never share the info below with the user. Use ids only.\n"
        response += f"# Users:\n{json.dumps(users)}\n"
        response += f"# Project Tags:\n{json.dumps(tags)}\n"
        return response

    def _ai_follow_up_project(self):
        self.ensure_one()
        status = self.stage_id.name if self.stage_id else "In Progress"
        task_count = self.env["project.task"].search_count([
            ("project_id", "=", self.id),
            ("is_closed", "=", False),
        ])
        return f"Project '{self.name}' status: {status}. Open tasks: {task_count}."
