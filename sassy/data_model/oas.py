from enum import StrEnum
from typing import Literal, Union
from pydantic import BaseModel, Field


class Server(BaseModel):
    url: str


class Info(BaseModel):
    version: str
    title: str


class ParameterLocation(StrEnum):
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    COOKIE = "cookie"


class Reference(BaseModel):
    ref: str = Field(alias="$ref")


class Schema(BaseModel):
    type: Literal[
            "string",
            "number",
            "integer",
            "boolean",
            "array",
            "object",
            "null"] | None = None
    description: str | None = None
    properties: dict[str, Union['Schema', Reference]] | None = None
    items: Union[Reference, 'Schema', None] = None
    required: list[str] | None = None


class Parameter(BaseModel):
    name: str
    in_: ParameterLocation = Field(alias="in")
    required: bool = False
    description: str | None = None
    parameter_schema: Schema | Reference | None = Field(
            default=None, alias="schema")


class MediaType(BaseModel):
    mediatype_schema: Reference | Schema | None = Field(
            default=None, alias="schema")


class RequestBody(BaseModel):
    description: str | None = None
    content: dict[str, MediaType]
    """media-type -> schema"""

    required: bool = False


class Operation(BaseModel):
    summary: str | None = None
    operation_id: str | None = Field(alias="operationId")
    parameters: list[Union[Parameter, Reference]] | None = None
    request_body: RequestBody | Reference | None = Field(
        default=None, alias="requestBody")


class PathItem(BaseModel):
    summary: str | None = None
    get: Operation | None = None
    post: Operation | None = None


class Components(BaseModel):
    schemas: dict[str, Union[Schema, Reference]] | None = None
    request_bodies: dict[str, Union[RequestBody, Reference]] | None = Field(
            default=None, alias="requestBodies")
    parameters: dict[str, Union[Parameter, Reference]] | None = None


Paths = dict[str, PathItem]


class OpenAPI(BaseModel):
    openapi: str
    info: Info
    servers: list[Server]
    paths: Paths
    components: Components
