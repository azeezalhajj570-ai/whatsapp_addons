{
    'name': 'WhatsApp Project Management AI',
    'version': '1.0.0',
    'category': 'Productivity',
    'summary': 'AI-driven Project Management Orchestrator for WhatsApp',
    'description': """
        Orchestrates incoming WhatsApp messages to create Projects, Tasks, and Leads using AI.
        Integrates whatsapp_evaluation with the AI module.
        Includes Product-Driven Service Catalog.
    """,
    'depends': [
        'whatsapp_evaluation',
        'ai',
        'crm',
        'project',
        'mail',
        'product', # Added product dependency explicitly
        'sale',    # Added sale dependency as we use sale_ok=True
        'sale_crm', # Required for quotation_count in CRM views
        'base_automation',
    ],
    'data': [
        'data/ai_agent_data.xml',
        'data/ir_actions_server_data.xml',
        'data/cleanup_unused_ai_actions.xml',
        'data/ir_actions_server_project_tools.xml',
        'data/whatsapp_message_ai_tools.xml',
        'data/whatsapp_ai_agent_automation.xml',
        'data/ai_topic_project_task.xml',
        'data/product_data.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_ai_menus.xml',
        'views/ir_actions_server_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'OPL-1',
}
