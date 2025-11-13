"""
Actions model for database service connections.

Defines the data model for actions that can be performed on web elements,
including their attributes and database interaction functions.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from common.service_connections.db_service.database import ActionTable


class ActionModel(BaseModel):
    """
    ActionModel is a Pydantic model that represents an action to be performed on a web element.

    Fields:
    - id (int): The unique identifier for the action.
    - action_method (str): The method name of the action (e.g., "click", "input_text").
    - action_parameters (dict): A dictionary of parameters required for the action (e.g.,
        text to input, index to select).
    - action_documentation (str): A description of what the action does.
    - created_at (datetime): The timestamp when the action was created.
    """

    id: Optional[int] = None
    action_method: Optional[str] = None
    action_parameters: Optional[dict] = None
    action_documentation: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __iter__(self):
        """
        Custom iterator to make the model compatible with table.html template.

        The template expects each row to be iterable and yield tuples of (field_name, field_value)
        where field_name is used for CSS classes and field_value is displayed.
        """
        for field_name, field_value in self.model_dump().items():
            yield (field_name, field_value)


################ Action Queries ################


def _convert_action_table_to_model(action_table) -> ActionModel:
    """Convert an ActionTable instance to an ActionModel instance."""
    return ActionModel(**action_table.__dict__)


def insert_action(action: ActionModel, session: Session, engine) -> ActionModel:
    """Insert a new action into the database."""
    if action.id:
        action.id = None

    with session(engine) as session:
        action.created_at = datetime.now()
        db_action = ActionTable(**action.model_dump())
        session.add(db_action)
        session.commit()
        session.refresh(db_action)
        return _convert_action_table_to_model(db_action)


def query_action_by_action_method(
    action_method: str, session: Session, engine
) -> Optional[ActionModel]:
    """Query an action by its method name."""
    with session(engine) as session:
        db_action = (
            session.query(ActionTable)
            .filter(ActionTable.action_method == action_method)
            .first()
        )
        if db_action:
            return _convert_action_table_to_model(db_action)
        return f"Action {action_method} not found"


def query_action_by_id(action_id: int, session: Session, engine) -> ActionModel:
    """Query an action by its ID."""
    with session(engine) as session:
        db_action = session.query(ActionTable).filter(ActionTable.id == action_id).first()
        if not db_action:
            raise ValueError(f"Action with ID {action_id} not found.")
        return _convert_action_table_to_model(db_action)


def query_all_actions(session: Session, engine) -> list[ActionModel]:
    """Query all actions from the database."""
    with session(engine) as session:
        db_actions = session.query(ActionTable).all()
        return [_convert_action_table_to_model(action) for action in db_actions]


def update_action_by_id(
    action_id: int, action: ActionModel, session: Session, engine
) -> ActionModel:
    """Update an existing action in the database by its ID."""
    with session(engine) as session:
        db_action = session.query(ActionTable).filter(ActionTable.id == action_id).first()
        if not db_action:
            raise ValueError(f"Action with ID {action_id} not found.")
        for key, value in action.model_dump(exclude_unset=True).items():
            setattr(db_action, key, value)
        db_action.updated_at = datetime.now()
        session.commit()
        session.refresh(db_action)
        return _convert_action_table_to_model(db_action)


def delete_action_by_id(action_id: int, session: Session, engine) -> int:
    """Delete an action from the database by its ID."""
    with session(engine) as session:
        db_action = session.query(ActionTable).filter(ActionTable.id == action_id).first()
        if not db_action:
            raise ValueError(f"Action with ID {action_id} not found.")
        session.delete(db_action)
        session.commit()
        return 1
