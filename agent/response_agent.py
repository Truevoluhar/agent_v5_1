import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model

from agent.generic_agent import GenericAgent
from agent.session import Session


def load_response_schema(schema_source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(schema_source, dict):
        return schema_source

    if isinstance(schema_source, (str, Path)):
        raw_value = str(schema_source).strip()
        if not raw_value:
            raise ValueError("Response schema source cannot be empty")

        if raw_value.startswith("{") or raw_value.startswith("["):
            return json.loads(raw_value)

        schema_path = Path(raw_value)
        if not schema_path.is_absolute():
            schema_path = Path.cwd() / schema_path

        with schema_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    raise TypeError("Unsupported response schema source type")


def _resolve_schema_type(schema: dict[str, Any], *, field_name: str) -> type[Any]:
    schema_type = schema.get("type")

    if schema_type == "string":
        return str

    if schema_type == "integer":
        return int

    if schema_type == "number":
        return float

    if schema_type == "boolean":
        return bool

    if schema_type == "array":
        item_schema = schema.get("items", {})
        item_type = _resolve_schema_type(item_schema, field_name=field_name)
        return list[item_type]

    if schema_type == "object" or "properties" in schema:
        nested_model_name = f"{field_name.capitalize()}Model"
        return create_dynamic_response_model_from_schema(
            schema,
            model_name=nested_model_name,
        )

    if "enum" in schema:
        enum_values = schema["enum"]
        if all(isinstance(value, str) for value in enum_values):
            enum_name = f"{field_name.capitalize()}Enum"
            return Enum(enum_name, {value: value for value in enum_values}, type=str)
        return str

    return Any


def _build_field_definition(
    schema: dict[str, Any],
    *,
    field_name: str,
    required: bool,
):
    annotation = _resolve_schema_type(schema, field_name=field_name)

    field_kwargs: dict[str, Any] = {}
    description = schema.get("description")
    if description:
        field_kwargs["description"] = description

    if not required:
        field_kwargs["default"] = None
        annotation = Optional[annotation]

    return annotation, Field(**field_kwargs)


def create_dynamic_response_model_from_schema(
    schema: dict[str, Any],
    *,
    model_name: str | None = None,
) -> type[BaseModel]:
    title = schema.get("title") or model_name or "DynamicResponse"
    properties = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    field_definitions: dict[str, tuple[Any, Field]] = {}
    for field_name, field_schema in properties.items():
        annotation, field_info = _build_field_definition(
            field_schema,
            field_name=field_name,
            required=field_name in required_fields,
        )
        field_definitions[field_name] = (annotation, field_info)

    config = ConfigDict(extra="forbid") if schema.get("additionalProperties") is False else None

    if config is None:
        return create_model(title, **field_definitions)

    return create_model(title, __config__=config, **field_definitions)


def create_dynamic_response_model(
    schema_source: str | Path | dict[str, Any],
    *,
    model_name: str | None = None,
) -> type[BaseModel]:
    schema = load_response_schema(schema_source)

    return create_dynamic_response_model_from_schema(
        schema,
        model_name=model_name or schema.get("title"),
    )


class ResponseAgent(GenericAgent):

    response_schema_source: str | Path | dict[str, Any] | None

    def __init__(
        self,
        id,
        name,
        model,
        api_key,
        base_url,
        temperature,
        resources_path,
        workspace_path,
        response_schema_source: str | Path | dict[str, Any] | None = None,
    ):
        self.response_schema_source = response_schema_source
        super().__init__(
            id=id,
            name=name,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            resources_path=resources_path,
            workspace_path=workspace_path,
        )

    def chat_structured(
        self,
        messages: list[dict[str, Any]],
        schema_source: str | Path | dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> BaseModel:
        schema_source = schema_source or self.response_schema_source
        if schema_source is None:
            raise ValueError("A response schema source must be provided.")

        response_model = create_dynamic_response_model(schema_source)

        request_messages = [
            {"role": "system", "content": self.system_message},
            {
                "role": "user",
                "content": "Create the final structured response strictly using the provided schema.",
            },
            *messages,
        ]

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=request_messages,
            response_format=response_model,
            temperature=self.temperature,
            timeout=None,
        )

        message = completion.choices[0].message

        if message.refusal:
            raise RuntimeError(f"Model refused the request: {message.refusal}")

        if message.parsed is None:
            raise RuntimeError(
                "Response could not be parsed. "
                f"Raw content: {message.content!r}"
            )

        parsed_response = message.parsed

        if session is not None:
            session.add_message(
                {
                    "role": "assistant",
                    "content": parsed_response.model_dump_json(indent=2),
                }
            )
        print(parsed_response.model_dump_json(indent=2))
        return parsed_response
