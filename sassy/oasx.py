from .data_model.jsons import JsonArray, JsonBoolean, JsonNull, JsonNumber, \
        JsonObject, JsonSchema, JsonString
from .data_model.oas import OpenAPI, Parameter, Reference, RequestBody, Schema


# TODO consolidate all those 'resolve' functions
def resolve_reference_schema(spec: OpenAPI, ref: Reference) -> Schema:
    segs = ref.ref.split('/')
    match segs:
        case ['#', 'components', 'schemas', *others]:
            schemas = spec.components.schemas
            assert schemas is not None
            match schemas['/'.join(others)]:
                case Schema() as sch:
                    return sch
                case Reference() as nref:
                    return resolve_reference_schema(spec, nref)
        case _:
            raise NotImplementedError(
                    f"unsupported schema reference f{ref.ref}")


def resolve_reference_requestbody(
        spec: OpenAPI, ref: Reference) -> RequestBody:
    segs = ref.ref.split('/')
    match segs:
        case ['#', 'components', 'requestBodies', *others]:
            requestBodies = spec.components.request_bodies
            assert requestBodies is not None
            match requestBodies['/'.join(others)]:
                case RequestBody() as rb:
                    return rb
                case Reference() as nref:
                    return resolve_reference_requestbody(spec, nref)
        case _:
            raise NotImplementedError(
                    f"unsupported request body reference f{ref.ref}")


def resolve_reference_parameter(spec: OpenAPI, ref: Reference) -> Parameter:
    segs = ref.ref.split('/')
    match segs:
        case ['#', 'components', 'parameters', *others]:
            parameters = spec.components.parameters
            assert parameters is not None
            match parameters['/'.join(others)]:
                case Parameter() as p:
                    return p
                case Reference() as nref:
                    return resolve_reference_parameter(spec, nref)
        case _:
            raise NotImplementedError(
                    f"unsupported parameter reference f{ref.ref}")


def as_json_schema(
        spec: OpenAPI,
        spec_sch: Schema | Reference,
        desc: str | None) -> JsonSchema:
    if isinstance(spec_sch, Reference):
        spec_sch = resolve_reference_schema(spec, spec_sch)

    if desc and spec_sch.description:
        d = f'{desc}\n{spec_sch.description}'
    elif desc:
        d = desc
    else:
        d = spec_sch.description

    match spec_sch.type:
        case "array":
            items = spec_sch.items
            assert items is not None
            if isinstance(items, Reference):
                items = resolve_reference_schema(spec, items)
            return JsonArray(
                items=as_json_schema(spec, items, None), description=d)
        case "number":
            return JsonNumber(description=d)
        case "string":
            return JsonString(description=d)
        case "boolean":
            return JsonBoolean(description=d)
        case "null":
            return JsonNull(description=d)
        case _:  # treating everything else as "object"
            props: dict[str, JsonSchema] = {}
            assert spec_sch.properties is not None
            for name, prop in spec_sch.properties.items():
                props[name] = as_json_schema(spec, prop, None)
            rqs = spec_sch.required if spec_sch.required is not None else []
            return JsonObject(properties=props, required=rqs, description=d)
