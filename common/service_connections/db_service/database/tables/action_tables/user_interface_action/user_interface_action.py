"""
Docstring for common.service_connections.db_service.database.tables.action_tables.user_interface_action.user_interface_action

User Interface Action table to manage user interface actions. This is going to be a 
very complicated table as it will need its own sub-queue of actions that will be
performed as part of the user interface action. I also want to allow UI actions to have
some level of intelligence so that they can make decisions based on the state of the UI.
Elements could change based on prior actions so I need to be able to handle that.
Also updating identifiers and pages as part of the action itself. 

Attributes:
    user_interface_action_id: The unique identifier for the user interface action.
    action_name: The name of the user interface action.
    description: A brief description of the user interface action.
    created_at: The timestamp when the action was created.
    updated_at: The timestamp when the action was last updated.
    owner_user_id: The ID of the user who owns the action.
    account_id: The ID of the account associated with the action.
    page_id: The ID of the page associated with the action.
    page_action_sequence: The sequence of actions to be performed on the page.
"""