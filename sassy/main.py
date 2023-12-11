import argparse
import json
import logging
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

from .config import Config

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


config = Config.from_env()
openai = OpenAI(api_key=config.OPENAI_API_KEY)


def render_openapi() -> str:
    env = Environment(loader=FileSystemLoader(searchpath="./tmpl"))
    template = env.get_template("api.json.j2")
    return template.render(host=config.SF_DOMAIN)


def spec_from_args(args: argparse.Namespace) -> str:
    if args.spec:
        with open(args.spec, 'r') as spec:
            return spec.read()
    return render_openapi()


def run():
    parser = argparse.ArgumentParser(
            prog='sassy', description='serve the APIs')

    subparsers = parser.add_subparsers(help='sub-command help', dest='command')

    _ = subparsers.add_parser('openapi')

    serve_parser = subparsers.add_parser('serve')
    serve_parser.add_argument('--spec')
    serve_parser.add_argument('--port', type=int, default=8080)
    serve_parser.add_argument('--host', default='0.0.0.0')
    serve_parser.add_argument('--assistant-id', default=None)

    args = parser.parse_args()

    if args.command == 'openapi':
        print(render_openapi())

    elif args.command == 'serve':
        from .server import app, Server

        server = Server(
            openai,
            app.logger,
            json.loads(spec_from_args(args)),
            config.DEFAULT_ACCESS_TOKEN)

        app.config["SERVER"] = server
        app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    run()
