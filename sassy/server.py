from abc import ABC, abstractmethod
import os
import time
import json
from typing import Any
from openai import OpenAI
from pydantic import BaseModel
from quart import Quart, Response, request, jsonify
from logging import Logger
from logging.config import dictConfig
from openai.types.beta.threads import \
        MessageContentText, \
        RequiredActionFunctionToolCall

from .functions import FunctionRegistry

dictConfig({
    'version': 1,
    'loggers': {
        'sassy.server': {
            'level': 'DEBUG',
        },
    },
})

ASSISTANT_DEF_FILE = '.assistant.json'
ASSISTANT_LOCK_FILE = '.assistant.json.lock'


class ChatRequest(BaseModel):
    thread_id: str
    content: str
    security: dict[str, str]
    """operation_id -> bearer token, __default__ will be used if no
    operation_id matches, if no __default__ no token is used"""


class BaseServer(ABC):
    _openai: OpenAI
    _assistant_id: str
    _logger: Logger

    @abstractmethod
    def _execute_tool_calls(
            self,
            thread_id: str,
            run_id: str,
            tool_calls: list[RequiredActionFunctionToolCall],
            security: dict[str, str]):
        pass

    def post_thread(self) -> dict[str, Any]:
        thread = self._openai.beta.threads.create()
        self._logger.info(thread)
        return thread.model_dump(exclude_unset=True)

    async def chat(self) -> Response:
        data = await request.json
        self._logger.info(f'received {data}')
        req = ChatRequest(**data)

        thread = self._openai.beta.threads.messages.create(
                thread_id=req.thread_id, role="user", content=req.content)

        run = self._openai.beta.threads.runs.create(
                thread_id=thread.thread_id,
                assistant_id=self._assistant_id)

        while True:
            run_status = self._openai.beta.threads.runs.retrieve(
                    thread_id=req.thread_id, run_id=run.id)
            print('.', end="", flush=True)

            if run_status.status == 'completed':
                print("")
                break

            elif run_status.status == 'requires_action':
                assert run_status.required_action
                print("")

                try:
                    self._execute_tool_calls(
                        req.thread_id,
                        run.id,
                        run_status
                            .required_action
                            .submit_tool_outputs
                            .tool_calls,
                        req.security)
                except Exception as e:
                    self._openai.beta.threads.runs.cancel(
                        run_id=run.id, thread_id=req.thread_id)
                    raise e

                time.sleep(1)  # Wait for a second before checking again

        # Retrieve and return the latest message from the assistant
        content = self._openai.beta.threads.messages.list(
                thread_id=req.thread_id
            ).data[0].content[0]

        match content:
            case MessageContentText():
                response = content.text.value
            case _:
                response = "unhandled message content type"

        self._logger.info(f"Assistant response: {response}")
        return jsonify({"response": response})


app = Quart(__name__)


def server(app) -> BaseServer:
    return app.config["SERVER"]


@app.route('/thread', methods=['POST'])
async def post_thread():
    return server(app).post_thread()


@app.route('/chat', methods=['POST'])
async def chat():
    return await server(app).chat()


class Server(BaseServer):
    _openai: OpenAI
    _assistant_id: str
    _logger: Logger
    _function_registry: FunctionRegistry

    def __init__(
            self,
            openai: OpenAI,
            logger: Logger,
            spec: Any,
            token: str | None) -> None:
        self._openai = openai
        self._logger = logger
        self._function_registry = FunctionRegistry.from_openapi_spec(
            spec, token)
        self._configure_assistant()

    def _configure_assistant(self) -> None:
        more_tools = self._function_registry.dump_assistant_tools()
        if os.path.exists(ASSISTANT_LOCK_FILE):
            with open(ASSISTANT_LOCK_FILE, 'r') as file:
                assistant_data = json.load(file)
                assistant_id = assistant_data['id']
                self._logger.info(
                        f'Loaded existing assistant ID {assistant_id}')
                self._assistant_id = assistant_id
            return

        with open(ASSISTANT_DEF_FILE, 'r') as def_f:
            assistant_def = json.load(def_f)

        tools = assistant_def["tools"]

        assistant = self._openai.beta.assistants.create(
            instructions=assistant_def['instructions'],
            model=assistant_def['model'],
            tools=tools + more_tools
        )

        with open(ASSISTANT_LOCK_FILE, 'w') as file:
            file.write(assistant.model_dump_json(indent=2, exclude_unset=True))

        self._assistant_id = assistant.id

    def _execute_tool_calls(
            self,
            thread_id: str,
            run_id: str,
            tool_calls: list[RequiredActionFunctionToolCall],
            security: dict[str, str]):
        for tool_call in tool_calls:
            self._logger.info(f"function name: {tool_call.function.name}")
            self._logger.info(
                "tool_call.function.arguments: "
                f"{tool_call.function.arguments}")

            arguments = json.loads(tool_call.function.arguments)

            fn_ident = tool_call.function.name

            bearer = security.get(fn_ident)
            if not bearer:
                bearer = security.get("__default__")

            output = self._function_registry.invoke(
                fn_ident, bearer, **arguments)

            self._logger.info(f"received openapi invoke result: {output}")
            self._openai.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=[{
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(output)}])
