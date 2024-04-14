from abc import ABC, abstractmethod
from typing import Any, Literal, Union

from pydantic import BaseModel
import requests

from .oasx import as_json_schema, resolve_reference_parameter, \
        resolve_reference_requestbody, resolve_reference_schema
from .data_model.jsons import JsonObject, JsonSchema
from .data_model.oas import OpenAPI, Operation, Parameter, \
    ParameterLocation, Reference, RequestBody, Schema


class FunctionInvoker(ABC):

    @abstractmethod
    def invoke(self, bearer: str | None, **kwargs) -> str:
        pass


Method = Literal["get", "post", "put", "delete", "patch"]


class RESTFunctionInvoker(FunctionInvoker):
    endpoint: str
    method: Method
    params_in: dict[str, ParameterLocation]
    # bearer token, later proabably need to implement some kind of
    # token/security providers, this is the fallback option if the token is not
    # provided by request
    security: str | None

    def __init__(
            self,
            endpoint: str,
            method: Method,
            params_in: dict[str, ParameterLocation],
            security: str | None) -> None:
        self.endpoint = endpoint
        self.method = method
        self.params_in = params_in
        self.security = security

    def _prep_request(self, bearer: str | None, **kwargs):
        params = {}
        request_body = {}
        headers = {}
        url = self.endpoint
        for k, v in kwargs.items():
            match self.params_in.get(k, None):
                case ParameterLocation.QUERY:
                    params[k] = v
                case ParameterLocation.PATH:
                    url = url.format(k=v)
                case ParameterLocation.HEADER | ParameterLocation.COOKIE:
                    raise NotImplementedError("Invalid parameter")
                case _:
                    request_body[k] = v

        if bearer:
            headers = {"Authorization": f"Bearer {bearer}"}
        elif self.security:
            headers = {"Authorization": f"Bearer {self.security}"}
        return params, request_body, url, headers

    def invoke(self, bearer: str | None, **kwargs) -> str:
        match self.method:
            case "get":
                params, _, url, headers = self._prep_request(bearer, **kwargs)
                return requests.get(url, params=params, headers=headers).json()
            case "post":
                params, body, url, headers = self._prep_request(
                        bearer, **kwargs)
                return requests.post(
                        url, params=params, json=body, headers=headers).json()

        raise NotImplementedError("not all methods are implemented yet")

    @classmethod
    def from_operation(
            cls,
            spec: OpenAPI,
            path: str,
            method: Method,
            op: Operation,
            token: str | None) -> 'RESTFunctionInvoker':
        endpoint = f"{spec.servers[0].url}{path}"
        params_in = {}
        if op.parameters:
            for p in op.parameters:
                if isinstance(p, Reference):
                    p = resolve_reference_parameter(spec, p)
                params_in[p.name] = p.in_
        return cls(endpoint, method, params_in, token)


class FunctionMeta(BaseModel):
    name: str
    description: str
    parameters: JsonSchema


class Function:
    fn_meta: FunctionMeta
    fn_invoker: FunctionInvoker

    def __init__(
            self, ident: str, description: str, parameters: JsonSchema,
            invoker: FunctionInvoker) -> None:
        self.fn_meta = FunctionMeta(
                name=ident, description=description, parameters=parameters)
        self.fn_invoker = invoker

    def invoke(self, bearer: str | None, **kwargs) -> str:
        return self.fn_invoker.invoke(bearer, **kwargs)

    def dump_tool_json(self) -> Any:
        return {
            "type": "function",
            "function": {
                "name": self.fn_meta.name,
                "description": self.fn_meta.description,
                "parameters": self.fn_meta.parameters.model_dump(
                    by_alias=True, exclude_none=True)
            }
        }

    @staticmethod
    def _resolve_operation_params(
            spec: OpenAPI,
            params: list[Union[Parameter, Reference]]) -> JsonSchema:
        props: dict[str, JsonSchema] = {}
        required: list[str] = []
        for p in params:
            if isinstance(p, Reference):
                p = resolve_reference_parameter(spec, p)
            assert p.name not in props, "Parameter name conflict dectected"
            assert p.parameter_schema is not None
            props[p.name] = as_json_schema(
                spec, p.parameter_schema, p.description)
            if p.required:
                required.append(p.name)
        return JsonObject(properties=props, required=required)

    @staticmethod
    def _resolve_requestbody_params(
            spec: OpenAPI, body: RequestBody | Reference) -> JsonSchema:

        if isinstance(body, Reference):
            body = resolve_reference_requestbody(spec, body)

        assert isinstance(body, RequestBody)
        desc = body.description
        if 'application/json' in body.content:
            match body.content['application/json'].mediatype_schema:
                case Schema() as s:
                    sch = s
                case Reference() as ref:
                    sch = resolve_reference_schema(spec, ref)
                case None:
                    raise Exception("Unexpected null value for "
                                    "'application/json' content")
            json_sch = as_json_schema(spec, sch, desc)

            return json_sch

        raise NotImplementedError("Only 'application/json' is supported")

    @classmethod
    def from_operation(
            cls,
            spec: OpenAPI,
            path: str,
            method: Method,
            op: Operation,
            token: str | None) -> 'Function':

        params: list[JsonSchema] = []
        if op.parameters:
            params.append(cls._resolve_operation_params(spec, op.parameters))
        if op.request_body:
            params.append(
                    cls._resolve_requestbody_params(spec, op.request_body))

        fnps = JsonObject(properties={})
        if len(params) == 1:
            fnps = params[0]
        elif len(params) > 1:
            raise NotImplementedError("Not supporting params in both request "
                                      "param and request body")

        name = op.operation_id if op.operation_id else ""
        description = op.summary if op.summary else ""

        invoker = RESTFunctionInvoker.from_operation(
                spec, path, method, op, token)

        return Function(
            ident=name,
            description=description,
            parameters=fnps,
            invoker=invoker
        )


class FunctionRegistry:
    _registry: dict[str, Function] = {}

    def import_openapi_spec(
            self,
            spec_json: Any,
            token: str | None = None) -> None:
        spec = OpenAPI(**spec_json)
        for path, path_item in spec.paths.items():
            if path_item.get:
                self.register_operation(
                        spec, path, "get", path_item.get, token)
            if path_item.post:
                self.register_operation(
                        spec, path, "post", path_item.post, token)

    @classmethod
    def from_openapi_spec(
            cls, spec_json: Any, token: str | None) -> 'FunctionRegistry':
        r = cls()
        r.import_openapi_spec(spec_json, token)
        return r

    def dump_assistant_tools(self) -> Any:
        """
        export assistant tools definition as a json object
        """

        return [fn.dump_tool_json() for _, fn in self._registry.items()]

    def register_operation(
            self, spec: OpenAPI, path: str, method: Method, op: Operation,
            token: str | None) -> None:
        ident = op.operation_id if op.operation_id else ""
        assert ident not in self._registry

        fn = Function.from_operation(spec, path, method, op, token)
        self._registry[ident] = fn

    def invoke(self, ident: str, bearer: str | None, **kwargs) -> str:
        """
        Invoke a function by it's identifier
        """

        fn = self._registry[ident]
        return fn.invoke(bearer, **kwargs)
