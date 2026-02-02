{
    'name': 'WhatsApp Project Management AI',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'AI-driven Project Management Orchestrator for WhatsApp',
    'description': """
        Orchestrates incoming WhatsApp messages to create Projects, Tasks, and Leads using AI.
        Integrates whatsapp_evaluation with the AI module.
    """,
    'depends': [
        'whatsapp_evaluation',
        'ai',
        'crm',
        'project',
        'mail',
    ],
    'data': [
        'data/ai_agent_data.xml',
        'data/ir_actions_server_data.xml',
        'views/whatsapp_message_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
