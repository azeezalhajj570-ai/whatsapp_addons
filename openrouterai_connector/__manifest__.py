{
    'name': 'OpenRouterAI Connector',
    'version': '1.0.0',
    'category': 'AI',
    'summary': 'OpenRouter provider integration and model sync',
    'description': """
        Adds OpenRouter as an AI provider, syncs the OpenRouter model catalog,
        and provides a client wrapper for chat completions with usage tracking.
    """,
    'depends': [
        'base',
        'mail',
        'ai',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/openrouter_cron_data.xml',
        'views/openrouter_provider_views.xml',
        'views/openrouter_company_views.xml',
        'views/openrouter_model_views.xml',
        'views/openrouter_request_log_views.xml',
        'views/openrouter_sync_wizard_views.xml',
        'views/openrouter_menu.xml',
    ],
    'application': False,
    'installable': True,
    'license': 'OPL-1',
}
