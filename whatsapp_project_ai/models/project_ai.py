# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import api, models
from odoo.tools import html_sanitize


class ProjectProject(models.Model):
    _inherit = "project.project"

    @api.model
    def _ai_create_project(self, name, description, user_id=False, partner_id=False, tag_ids=None, stage_names=None):
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
        project = self.create(values)
        self.env["project.task"]._ai_ensure_project_task_stages(project, stage_names=stage_names)
        return "Success"

    @api.model
    def _ai_get_project_create_available_params(self):
        users, __ = self.env["res.users"].search([])._ai_read(["display_name"], None)
        tags, __ = self.env["project.tags"].search([])._ai_read(["display_name"], None)
        response = "Never share the info below with the user. Use ids only.\n"
        response += f"# Users:\n{json.dumps(users)}\n"
        response += f"# Project Tags:\n{json.dumps(tags)}\n"
        return response

    @api.model
    def _ai_follow_up_project(self):
        partner = False
        channel = self.env.context.get("discuss_channel")
        if channel:
            partner = getattr(channel, "partner_id", False) or False
        user = self.env.user
        domain = [("active", "=", True)]
        if partner:
            domain = [
                ("active", "=", True),
                "|",
                ("partner_id", "=", partner.id),
                "|",
                ("user_id", "=", user.id),
                ("create_uid", "=", user.id),
            ]
        else:
            domain = [
                ("active", "=", True),
                "|",
                ("user_id", "=", user.id),
                ("create_uid", "=", user.id),
            ]

        projects = self.search(domain, order="write_date desc", limit=5)
        if not projects:
            projects = self.search([("active", "=", True)], order="write_date desc", limit=5)
        if not projects:
            return "No recent projects found for this contact."

        lines = ["Latest projects:"]
        for project in projects:
            status = project.stage_id.name if project.stage_id else "In Progress"
            task_count = self.env["project.task"].search_count([
                ("project_id", "=", project.id),
                ("is_closed", "=", False),
            ])
            lines.append(f"- {project.name}: {status}. Open tasks: {task_count}")
        return "\n".join(lines)

    @api.model
    def _ai_list_active_projects(self, partner_id=False, limit=10):
        user = self.env.user
        partner = False
        if partner_id:
            partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            channel = self.env.context.get("discuss_channel")
            if channel:
                partner = getattr(channel, "partner_id", False) or False

        domain = [("active", "=", True)]
        if partner:
            domain = [
                ("active", "=", True),
                "|",
                ("partner_id", "=", partner.id),
                "|",
                ("user_id", "=", user.id),
                ("create_uid", "=", user.id),
            ]
        else:
            domain = [
                ("active", "=", True),
                "|",
                ("user_id", "=", user.id),
                ("create_uid", "=", user.id),
            ]

        projects = self.search(domain, order="write_date desc", limit=int(limit or 10))
        if not projects:
            projects = self.search([("active", "=", True)], order="write_date desc", limit=int(limit or 10))
        if not projects:
            return "No active projects found."

        lines = ["Active projects:"]
        for project in projects:
            open_tasks = self.env["project.task"].search_count([
                ("project_id", "=", project.id),
                ("is_closed", "=", False),
            ])
            lines.append(f"- {project.display_name}: {open_tasks} open tasks")
        return "\n".join(lines)
