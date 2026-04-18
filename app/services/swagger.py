from flasgger import Swagger

swagger = Swagger()

def init_swagger(app):
    app.config['SWAGGER'] = {
        'title': 'Turismo App API',
        'uiversion': 3,
        'openapi': '3.0.1',
        'specs_route': '/docs'
    }
    swagger.init_app(app)