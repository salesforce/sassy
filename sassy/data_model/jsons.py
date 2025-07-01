from typing import Literal
from pydantic import BaseModel


class JsonSchema(BaseModel):
    type: Literal["object", "array", "number", "string", "boolean", "null"]
    description: str | None = None


class JsonObject(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "object"
    properties: dict[str, JsonSchema]
    required: list[str] = []


class JsonArray(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "array"
    items: JsonSchema


class JsonNumber(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "number"


class JsonString(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "string"


class JsonBoolean(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "boolean"


class JsonNull(JsonSchema):
    type: Literal[
            "object",
            "array",
            "number",
            "string",
            "boolean",
            "null"] = "null"
