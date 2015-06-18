import pathlib
import flask
import json
import pytest
import requests
import logging
import _pytest.monkeypatch

from connexion.app import App

logging.basicConfig(level=logging.DEBUG)

TEST_FOLDER = pathlib.Path(__file__).parent
SPEC_FOLDER = TEST_FOLDER / "fakeapi"


class FakeResponse:
    def __init__(self, status_code: int, text: str):
        self.status_code = status_code
        self.text = text
        self.ok = status_code == 200

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def oauth_requests(monkeypatch: '_pytest.monkeypatch.monkeypatch'):
    def fake_get(url: str, params: dict=None):
        params = params or {}
        if url == "https://ouath.example/token_info":
            token = params['access_token']
            if token == "100":
                return FakeResponse(200, '{"scope": ["myscope"]}')
            if token == "200":
                return FakeResponse(200, '{"scope": ["wrongscope"]}')
            if token == "300":
                return FakeResponse(404, '')
        return url

    monkeypatch.setattr(requests, 'get', fake_get)


@pytest.fixture
def app():
    app = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app.add_api('api.yaml')
    return app


def test_app(app):
    assert app.port == 5001

    app_client = app.app.test_client()
    swagger_ui = app_client.get('/v1.0/ui/')  # type: flask.Response
    assert swagger_ui.status_code == 200
    assert b"Swagger UI" in swagger_ui.data

    swagger_icon = app_client.get('/v1.0/ui/images/favicon.ico')  # type: flask.Response
    assert swagger_icon.status_code == 200

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.status_code == 200
    assert get_bye.data == b'Goodbye jsantos'

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'


def test_produce_decorator(app):
    app_client = app.app.test_client()

    get_bye = app_client.get('/v1.0/bye/jsantos')  # type: flask.Response
    assert get_bye.content_type == 'text/plain; charset=utf-8'


def test_errors(app):
    app_client = app.app.test_client()

    greeting404 = app_client.get('/v1.0/greeting')  # type: flask.Response
    assert greeting404.content_type == 'application/problem+json'
    assert greeting404.status_code == 404
    error404 = json.loads(greeting404.data.decode('utf-8'))
    assert error404['type'] == 'about:blank'
    assert error404['title'] == 'Not Found'
    assert error404['detail'] == 'The requested URL was not found on the server.  ' \
                                 'If you entered the URL manually please check your spelling and try again.'
    assert error404['status'] == 404
    assert 'instance' not in error404

    get_greeting = app_client.get('/v1.0/greeting/jsantos')  # type: flask.Response
    assert get_greeting.content_type == 'application/problem+json'
    assert get_greeting.status_code == 405
    error405 = json.loads(get_greeting.data.decode('utf-8'))
    assert error405['type'] == 'about:blank'
    assert error405['title'] == 'Method Not Allowed'
    assert error405['detail'] == 'The method is not allowed for the requested URL.'
    assert error405['status'] == 405
    assert 'instance' not in error405

    get500 = app_client.get('/v1.0/except')  # type: flask.Response
    assert get500.content_type == 'application/problem+json'
    assert get500.status_code == 500
    error500 = json.loads(get500.data.decode('utf-8'))
    assert error500['type'] == 'about:blank'
    assert error500['title'] == 'Internal Server Error'
    assert error500['detail'] == 'The server encountered an internal error and was unable to complete your request.  ' \
                                 'Either the server is overloaded or there is an error in the application.'
    assert error500['status'] == 500
    assert 'instance' not in error500

    get_problem = app_client.get('/v1.0/problem')  # type: flask.Response
    assert get_problem.content_type == 'application/problem+json'
    assert get_problem.status_code == 418
    error_problem = json.loads(get_problem.data.decode('utf-8'))
    assert error_problem['type'] == 'http://www.example.com/error'
    assert error_problem['title'] == 'Some Error'
    assert error_problem['detail'] == 'Something went wrong somewhere'
    assert error_problem['status'] == 418
    assert error_problem['instance'] == 'instance1'

    get_problem2 = app_client.get('/v1.0/other_problem')  # type: flask.Response
    assert get_problem2.content_type == 'application/problem+json'
    assert get_problem2.status_code == 418
    error_problem2 = json.loads(get_problem2.data.decode('utf-8'))
    assert error_problem2['type'] == 'about:blank'
    assert error_problem2['title'] == 'Some Error'
    assert error_problem2['detail'] == 'Something went wrong somewhere'
    assert error_problem2['status'] == 418
    assert error_problem2['instance'] == 'instance1'


def test_jsonifier(app):
    app_client = app.app.test_client()

    post_greeting = app_client.post('/v1.0/greeting/jsantos', data={})  # type: flask.Response
    assert post_greeting.status_code == 200
    assert post_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(post_greeting.data.decode('utf-8'))
    assert greeting_reponse['greeting'] == 'Hello jsantos'

    get_list_greeting = app_client.get('/v1.0/list/jsantos', data={})  # type: flask.Response
    assert get_list_greeting.status_code == 200
    assert get_list_greeting.content_type == 'application/json'
    greeting_reponse = json.loads(get_list_greeting.data.decode('utf-8'))
    assert len(greeting_reponse) == 2
    assert greeting_reponse[0] == 'hello'
    assert greeting_reponse[1] == 'jsantos'

    get_greetings = app_client.get('/v1.0/greetings/jsantos', data={})  # type: flask.Response
    assert get_greetings.status_code == 200
    assert get_greetings.content_type == 'application/x.connexion+json'
    greetings_reponse = json.loads(get_greetings.data.decode('utf-8'))
    assert len(greetings_reponse) == 1
    assert greetings_reponse['greetings'] == 'Hello jsantos'


def test_pass_through(app):
    app_client = app.app.test_client()

    response = app_client.get('/v1.0/multimime', data={})  # type: flask.Response
    assert response.status_code == 200


def test_security(oauth_requests):
    app1 = App(__name__, 5001, SPEC_FOLDER, debug=True)
    app1.add_api('api.yaml')
    assert app1.port == 5001

    app_client = app1.app.test_client()
    get_bye_no_auth = app_client.get('/v1.0/byesecure/jsantos')  # type: flask.Response
    assert get_bye_no_auth.status_code == 401

    headers = {"Authorization": "Bearer 100"}
    get_bye_good_auth = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_good_auth.status_code == 200
    assert get_bye_good_auth.data == b'Goodbye jsantos (Secure)'

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 200"}
    get_bye_wrong_scope = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_wrong_scope.status_code == 401

    app_client = app1.app.test_client()
    headers = {"Authorization": "Bearer 300"}
    get_bye_bad_token = app_client.get('/v1.0/byesecure/jsantos', headers=headers)  # type: flask.Response
    assert get_bye_bad_token.status_code == 401