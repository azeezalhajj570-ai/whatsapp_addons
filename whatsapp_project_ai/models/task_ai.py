# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import html_sanitize


class ProjectTask(models.Model):
    _inherit = "project.task"

    _AI_DEFAULT_STAGE_NAMES = ("Todo", "Doing", "Review", "Done")

    @api.model
    def _ai_normalize_stage_names(self, stage_names=None):
        names = stage_names or self._AI_DEFAULT_STAGE_NAMES
        cleaned = []
        seen = set()
        for stage_name in names:
            if not isinstance(stage_name, str):
                continue
            value = stage_name.strip()
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(value)
        return cleaned or list(self._AI_DEFAULT_STAGE_NAMES)

    @api.model
    def _ai_ensure_project_task_stages(self, project, stage_names=None):
        stages = self.env["project.task.type"]
        if not project:
            return stages

        stage_model = self.env["project.task.type"].sudo()
        wanted_names = self._ai_normalize_stage_names(stage_names)

        for sequence, stage_name in enumerate(wanted_names, start=1):
            stage = stage_model.search([
                ("name", "=ilike", stage_name),
                "|",
                ("project_ids", "=", False),
                ("project_ids", "in", project.id),
            ], order="sequence,id", limit=1)
            if not stage:
                stage = stage_model.create({
                    "name": stage_name,
                    "sequence": sequence * 10,
                    "project_ids": [(4, project.id)],
                })
            elif stage.project_ids and project.id not in stage.project_ids.ids:
                stage.write({"project_ids": [(4, project.id)]})
            stages |= stage

        return stages.sorted(key=lambda stage: (stage.sequence, stage.id))

    @api.model
    def _ai_create_task(self, name, description, project_id, user_id=False, tag_ids=None, deadline_days=None, stage_names=None):
        project = self.env["project.project"].browse(project_id).exists()
        if not project:
            return "Error: target project was not found."

        stages = self._ai_ensure_project_task_stages(project, stage_names=stage_names)
        values = {
            "name": name,
            "description": html_sanitize(description or ""),
            "project_id": project.id,
            "stage_id": stages[:1].id if stages else False,
        }
        if user_id:
            values["user_ids"] = [(6, 0, [user_id])]
        if tag_ids:
            values["tag_ids"] = [(6, 0, tag_ids)]
        if deadline_days:
            values["date_deadline"] = fields.Date.context_today(self) + timedelta(days=int(deadline_days))
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

    @api.model
    def _ai_follow_up_task(self):
        partner = False
        channel = self.env.context.get("discuss_channel")
        if channel:
            partner = getattr(channel, "partner_id", False) or False
        if not partner and self.env.user:
            partner = self.env.user.partner_id

        domain = []
        if partner:
            domain.append(("partner_id", "=", partner.id))

        tasks = self.search(domain, order="write_date desc", limit=5)
        if not tasks:
            return "No recent tasks found for this contact."

        lines = ["Latest tasks:"]
        for task in tasks:
            status = task.stage_id.name if task.stage_id else "In Progress"
            project_name = task.project_id.display_name if task.project_id else "No Project"
            lines.append(f"- {task.name} ({project_name}): {status}")
        return "\n".join(lines)
