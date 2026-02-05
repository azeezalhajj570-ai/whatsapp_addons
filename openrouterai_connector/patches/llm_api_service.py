# -*- coding: utf-8 -*-
"""Patch ai.utils.llm_api_service to add OpenRouter support.

This is loaded by openrouterai_connector to avoid editing core ai module files.
"""
import json

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.ai.utils import llm_api_service


LLMApiService = llm_api_service.LLMApiService


_original_init = LLMApiService.__init__
_original_get_api_token = LLMApiService._get_api_token
_original_request_llm = LLMApiService._request_llm
_original_build_tool_call_response = LLMApiService._build_tool_call_response


def _init(self, env, provider="openai"):
    if provider == "openrouter":
        self.provider = provider
        self.base_url = "https://openrouter.ai/api/v1"
        self.env = env
        return
    return _original_init(self, env, provider)


def _get_api_token(self):
    if self.provider == "openrouter":
        provider = self.env["ai.openrouter.provider"].sudo().search([("active", "=", True)], limit=1)
        if provider and provider.api_key:
            return provider.api_key
        param = self.env["ir.config_parameter"].sudo().get_param("ai.openrouter_key")
        if param:
            return param
        return llm_api_service.os.getenv("OPENROUTER_API_KEY") or ""
    return _original_get_api_token(self)


def _request_llm(self, *args, **kwargs):
    if self.provider == "openrouter":
        return _request_llm_openrouter(self, *args, **kwargs)
    return _original_request_llm(self, *args, **kwargs)


def _build_tool_call_response(self, tool_call_id, return_value):
    if self.provider == "openrouter":
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": str(return_value),
        }
    return _original_build_tool_call_response(self, tool_call_id, return_value)


def _request_llm_openrouter(
    self, llm_model, system_prompts, user_prompts, tools=None,
    files=None, schema=None, temperature=0.2, inputs=(), web_grounding=False
):
    if files:
        raise NotImplementedError("OpenRouter chat completions does not support file uploads here.")
    if web_grounding:
        raise NotImplementedError("OpenRouter web grounding is not supported in this integration.")
    if schema:
        raise NotImplementedError("OpenRouter does not support structured output in this integration.")

    messages = []
    for prompt in system_prompts or []:
        messages.append({"role": "system", "content": prompt})
    for prompt in user_prompts or []:
        messages.append({"role": "user", "content": prompt})
    if inputs:
        messages.extend(inputs)

    body = {
        "model": llm_model,
        "messages": messages,
        "temperature": temperature,
    }

    if tools:
        body["tools"] = [{
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": tool_parameter_schema,
            },
        } for tool_name, (tool_description, __, __, tool_parameter_schema) in tools.items()]

    llm_response = self._request(
        "post",
        "/chat/completions",
        self._get_base_headers(),
        body,
    )

    to_call = []
    response = []
    next_inputs = list(inputs or ())

    choices = llm_response.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        if tool_calls := message.get("tool_calls"):
            for call in tool_calls:
                func = call.get("function") or {}
                try:
                    arguments = json.loads(func.get("arguments") or "{}")
                except json.decoder.JSONDecodeError:
                    llm_api_service._logger.error("OpenRouter: Malformed arguments: %s", call)
                    continue
                to_call.append((func.get("name"), call.get("id"), arguments))
            next_inputs.append({"role": "assistant", "tool_calls": tool_calls})
        if content := message.get("content"):
            response.append(content)

    return response, to_call, next_inputs


LLMApiService.__init__ = _init
LLMApiService._get_api_token = _get_api_token
LLMApiService._request_llm = _request_llm
LLMApiService._build_tool_call_response = _build_tool_call_response
LLMApiService._request_llm_openrouter = _request_llm_openrouter
