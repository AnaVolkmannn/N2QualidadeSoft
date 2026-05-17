import subprocess
import time
import sys
from loguru import logger

class ApplicationBootstrap:
	process: subprocess.Popen
	repo_absolute_path: str
	# Gerenciador de dependência java:
	# - Maven
	# - Gradle
	dep_man: str
	# API URL: localhost:8080 (example)
	api_url: str
	# Endpoints to test
	api_endpoints: list[str]
	# Application type
	# - SpringBoot
	# - Quarkus
	application_type: str

	def __init__(self, repo_absolute_path: str, dep_man: str, api_url: str, api_endpoints: list[str]):
		self.repo_absolute_path = repo_absolute_path
		self.dep_man = dep_man
		self.api_url = api_url
		self.api_endpoints = api_endpoints

	def run(self):
		command_args: list[str]

		if self.dep_man == "maven":
			if self.application_type == "quarkus":
				command_args = ["mvn", "-f", self.repo_absolute_path, "quarkus:dev"]
			
			if self.application_type == "spring":
				command_args = ["mvn", "-f", self.repo_absolute_path, "spring-boot:run"]
		
		if self.dep_man == "gradle":
			if self.application_type == "quarkus":
				command_args = ["gradle", "-p", self.repo_absolute_path, "quarkusDev"]
			
			if self.application_type == "spring":
				command_args = ["gradle", "-p", self.repo_absolute_path, "bootRun"]

		logger.info(f"Starting application: {self.repo_absolute_path}")

		try:
			with open("java_output.log", "w") as log_file:
				self.process = subprocess.Popen(
					command_args,
					stdout=log_file,
					stderr=subprocess.PIPE,
					text=True
				)

				time.sleep(2)
				status_code = self.process.poll()
        		
				if status_code is not None:
					_, errors = self.processo.communicate()
					logger.error(f"The Java process failed to start. code={status_code} err={errors}")
					sys.exit(1)
				
				logger.info("Application Java started.")
		except FileNotFoundError:
			logger.error("The executable 'java' was not found in your PATH.")
			sys.exit(1)
