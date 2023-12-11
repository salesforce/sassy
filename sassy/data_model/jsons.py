from typing import Literal
from pydantic import BaseModel


class JsonSchema(BaseModel):
    type: Literal["object", "array", "number", "string", "boolean", "null"]
    description: str | None = None


class JsonObject(JsonSchema):
    type: Literal["object"] = "object"
    properties: dict[str, JsonSchema]
    required: list[str] = []


class JsonArray(JsonSchema):
    type: Literal["array"] = "array"
    items: JsonSchema


class JsonNumber(JsonSchema):
    type: Literal["number"] = "number"


class JsonString(JsonSchema):
    type: Literal["string"] = "string"


class JsonBoolean(JsonSchema):
    type: Literal["boolean"] = "boolean"


class JsonNull(JsonSchema):
    type: Literal["null"] = "null"
