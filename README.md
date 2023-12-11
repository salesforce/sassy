# sassy

> lively, bold, and full of spirit; cheeky. -- Definitions from Oxford Languages

Sassy is a server that interact with chat clients, chat services, assistant
services and function providers, to power seemless AI assitant based
applications.

# Setup

Sassy is implemented in python and uses [poetry](https://python-poetry.org/) to
manage setup and dependencies.

Follow poetry's [documentation](https://python-poetry.org/docs/) to install and
setup peotry.

Ensure that this dependency is present and the paths are correct by running:

```
poetry install
```

Start the server by running:

```
poetry run main serve
```

It will start a service and using the default sample OAS template in
`tmpl/api.json.j2`. The template consists of a few example open API spec with
[Salesforce's REST
API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_rest.htm)
to show case the functionality and capability.

You can also pass your own Open API spec with the `--spec` flag. i.e.:

```
poetry run main serve --spec /path/to/your/own/oas.json
```
