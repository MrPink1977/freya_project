"""
Validation utilities for Pydantic schema validation.

Provides helper functions for validating message payloads and tool parameters,
with proper error handling and logging.
"""
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from freya.exceptions import AgentMessageError, ToolInputError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def validate_message_payload(payload: dict, schema: Type[T], agent_id: str = "unknown") -> T:
    """
    Validate agent message payload against Pydantic schema.

    Args:
        payload: Raw message payload dictionary
        schema: Pydantic model class to validate against
        agent_id: Agent identifier for error context

    Returns:
        Validated Pydantic model instance

    Raises:
        AgentMessageError: If validation fails

    Example:
        >>> payload = {"text": "Hello", "role": "user"}
        >>> validated = validate_message_payload(payload, DialogRequestPayload, "dialog_agent")
        >>> print(validated.text)
        "Hello"
    """
    try:
        return schema(**payload)
    except ValidationError as exc:
        error_details = exc.errors()
        logger.error(
            "Invalid message payload for %s: %s",
            agent_id,
            error_details,
            exc_info=True
        )
        raise AgentMessageError(
            f"Invalid message payload: {error_details[0]['msg']}",
            agent_id=agent_id,
            validation_errors=error_details,
            payload=payload
        )


def validate_tool_parameters(params: dict, schema: Type[T], tool_name: str) -> T:
    """
    Validate tool parameters against Pydantic schema.

    Args:
        params: Raw tool parameter dictionary
        schema: Pydantic model class to validate against
        tool_name: Tool identifier for error context

    Returns:
        Validated Pydantic model instance

    Raises:
        ToolInputError: If validation fails

    Example:
        >>> params = {"expression": "2 + 2"}
        >>> validated = validate_tool_parameters(params, CalculatorParams, "calculator")
        >>> print(validated.expression)
        "2 + 2"
    """
    try:
        return schema(**params)
    except ValidationError as exc:
        error_details = exc.errors()
        logger.error(
            "Invalid tool parameters for %s: %s",
            tool_name,
            error_details,
            exc_info=True
        )
        raise ToolInputError(
            f"Invalid tool parameters: {error_details[0]['msg']}",
            tool_name=tool_name,
            validation_errors=error_details,
            input_data=params
        )
