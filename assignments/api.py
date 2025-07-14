from ninja import NinjaAPI, Swagger

api = NinjaAPI(docs=Swagger(settings={"persistAuthorization": True}))
