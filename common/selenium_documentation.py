# =====================================
# Pydantic Models for Method Documentation
# =====================================


import inspect
from typing import Dict, List, Optional
from pydantic import BaseModel

from fts.common.selenium_controller import SeleniumController


class MethodParameter(BaseModel):
    """Represents a method parameter with its type information and default value."""

    name: str
    type_hint: str
    default_value: Optional[str] = None
    is_optional: bool = False

    class Config:
        """Pydantic configuration."""

        frozen = True


class MethodDocumentation(BaseModel):
    """Comprehensive documentation for a SeleniumController method."""

    method_name: str
    docstring: str
    parameters: List[MethodParameter]
    return_type: str

    class Config:
        """Pydantic configuration."""

        frozen = True


def get_selenium_controller_methods_documentation() -> Dict[str, MethodDocumentation]:
    """
    Builds a comprehensive dictionary of all SeleniumController methods with their documentation,
    parameters, type hints, and return types.

    Returns:
        Dict[str, MethodDocumentation]: Dictionary mapping method names to MethodDocumentation objects
                                       containing full method information including parameters and types.
    """
    methods_doc = {}

    # Get all methods from the SeleniumController class
    for name, method in inspect.getmembers(
        SeleniumController, predicate=inspect.isfunction
    ):
        # Skip private methods (those starting with underscore)
        if not name.startswith("_"):
            # Get method signature for parameter analysis
            try:
                signature = inspect.signature(method)
                parameters = []

                # Process each parameter
                for param_name, param in signature.parameters.items():
                    # Skip 'self' parameter
                    if param_name == "self":
                        continue

                    # Extract type hint information
                    type_hint = "Any"
                    if param.annotation != inspect.Parameter.empty:
                        # Handle different annotation types
                        if hasattr(param.annotation, "__name__"):
                            type_hint = param.annotation.__name__
                        elif hasattr(param.annotation, "_name"):
                            # Handle typing constructs like Optional, Union, etc.
                            type_hint = str(param.annotation)
                        else:
                            type_hint = str(param.annotation)

                    # Extract default value information
                    default_value = None
                    is_optional = False
                    if param.default != inspect.Parameter.empty:
                        if param.default is None:
                            default_value = "None"
                            is_optional = True
                        else:
                            default_value = str(param.default)
                            is_optional = True

                    # Create parameter object
                    method_param = MethodParameter(
                        name=param_name,
                        type_hint=type_hint,
                        default_value=default_value,
                        is_optional=is_optional,
                    )
                    parameters.append(method_param)

                # Extract return type annotation
                return_type = "None"
                if signature.return_annotation != inspect.Signature.empty:
                    if hasattr(signature.return_annotation, "__name__"):
                        return_type = signature.return_annotation.__name__
                    elif hasattr(signature.return_annotation, "_name"):
                        return_type = str(signature.return_annotation)
                    else:
                        return_type = str(signature.return_annotation)

                # Get docstring
                docstring = inspect.getdoc(method)
                if not docstring:
                    docstring = "No documentation available"

                # Create method documentation object
                method_doc = MethodDocumentation(
                    method_name=name,
                    docstring=docstring,
                    parameters=parameters,
                    return_type=return_type,
                )

                methods_doc[name] = method_doc

            except Exception as e:
                # Fallback for methods that can't be introspected
                method_doc = MethodDocumentation(
                    method_name=name,
                    docstring=f"Error extracting documentation: {str(e)}",
                    parameters=[],
                    return_type="Unknown",
                )
                methods_doc[name] = method_doc

    return methods_doc


# Check if all the methods in the FrontendDriver class are in the FrontendActionsEnum
if __name__ == "__main__":
    print(get_selenium_controller_methods_documentation())
