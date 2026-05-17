from loguru import logger

class ApplicationBootstrap:
	application_absolute_path: str
	# Gerenciador de dependência java:
	# - Maven
	# - Gradle
	dep_man: str
	# API URL: localhost:8080 (example)
	api_url: str
	# Endpoints to test
	api_endpoints: list[str]

	def __init__(self, application_absolute_path: str, dep_man: str, api_url: str, api_endpoints: list[str]):
		self.application_absolute_path = application_absolute_path
		self.dep_man = dep_man
		self.api_url = api_url
		self.api_endpoints = api_endpoints

	def run(self):
		logger.info(f"Starting application: {self.application_absolute_path}")
		

