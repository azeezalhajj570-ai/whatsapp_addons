# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

import requests

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class EvolutionClient(models.AbstractModel):
    _name = 'evolution.instance.client'
    _description = 'Evolution API Client'

    def _build_base_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('evolution_instance_manager.base_url')
        if not base_url:
            raise UserError(_('Please configure Evolution Base URL in Settings.'))
        return base_url.rstrip('/')

    def _build_headers(self):
        api_key = self.env['ir.config_parameter'].sudo().get_param('evolution_instance_manager.server_api_key')
        if not api_key:
            raise UserError(_('Please configure Evolution Server API Key in Settings.'))
        return {
            'apikey': api_key,
            'Content-Type': 'application/json',
        }

    def _request(self, method, endpoint, payload=None, timeout=(10, 30)):
        url = '%s%s' % (self._build_base_url(), endpoint)
        headers = self._build_headers()

        safe_headers = dict(headers)
        safe_headers['apikey'] = '***'
        _logger.info('Evolution API request %s %s headers=%s payload=%s', method, url, safe_headers, payload)

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.exceptions.Timeout as exc:
            raise UserError(_('Evolution API request timed out.')) from exc
        except requests.exceptions.RequestException as exc:
            raise UserError(_('Could not reach Evolution API server: %s') % exc) from exc

        try:
            response_data = response.json() if response.text else {}
        except ValueError:
            response_data = {}

        if not response.ok:
            error_message = self._extract_error_message(response_data) or response.text
            _logger.error(
                'Evolution API error %s %s status=%s response=%s',
                method,
                url,
                response.status_code,
                json.dumps(response_data) if response_data else response.text,
            )
            raise UserError(_('Evolution API error (%s): %s') % (response.status_code, error_message or _('Unknown error')))

        if isinstance(response_data, dict):
            return response_data
        if isinstance(response_data, list):
            return {'data': response_data}
        if isinstance(response_data, str):
            return {'message': response_data}
        return {}

    @staticmethod
    def _extract_error_message(payload):
        if isinstance(payload, str):
            return payload
        if isinstance(payload, list):
            return '; '.join(str(item) for item in payload if item)
        if not isinstance(payload, dict):
            return None

        # Common Evolution error shape:
        # {"status":403,"error":"Forbidden","response":{"message":["..."]}}
        nested = payload.get('response')
        if isinstance(nested, dict):
            nested_message = nested.get('message')
            if isinstance(nested_message, list):
                return '; '.join(str(item) for item in nested_message if item)
            if nested_message:
                return str(nested_message)

        message = payload.get('message')
        if isinstance(message, list):
            return '; '.join(str(item) for item in message if item)
        if message:
            return str(message)

        error = payload.get('error')
        if error:
            return str(error)
        return None

    def create_instance(self, payload):
        return self._request('POST', '/instance/create', payload=payload)

    def connection_state(self, instance_name):
        return self._request('GET', '/instance/connectionState/%s' % instance_name)

    @staticmethod
    def _is_404_error(error):
        return '(404)' in str(error)

    def fetch_qr(self, instance_name):
        # Endpoint naming varies across Evolution versions, so we try common routes.
        attempts = [
            ('GET', '/instance/connect/%s' % instance_name, None),
            ('GET', '/instance/qr/%s' % instance_name, None),
        ]
        last_error = None
        for method, endpoint, payload in attempts:
            try:
                return self._request(method, endpoint, payload=payload)
            except UserError as exc:
                last_error = exc
                if not self._is_404_error(exc):
                    raise
        raise last_error

    def fetch_pairing_code(self, instance_name, phone_number):
        # Endpoint and payload shape differ by Evolution release; try common options.
        attempts = [
            ('POST', '/instance/connect/%s' % instance_name, {'number': phone_number}),
            ('POST', '/instance/pairingCode/%s' % instance_name, {'number': phone_number}),
            ('GET', '/instance/connect/%s?number=%s' % (instance_name, phone_number), None),
        ]
        last_error = None
        for method, endpoint, payload in attempts:
            try:
                return self._request(method, endpoint, payload=payload)
            except UserError as exc:
                last_error = exc
                if not self._is_404_error(exc):
                    raise
        raise last_error
