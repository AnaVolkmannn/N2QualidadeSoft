import subprocess
import time
import sys
from loguru import logger
from enums import BuildToolType, ApplicationType

class ApplicationBootstrap:
    process: subprocess.Popen
    repo_absolute_path: str
    build_tool: BuildToolType
    api_url: str
    api_endpoints: list[str]
    application_type: ApplicationType
    log_file = None
    log_error = None

    def __init__(
            self, repo_absolute_path: str,
            application_type: ApplicationType, 
            build_tool: BuildToolType,
            api_url: str,
            api_endpoints: list[str]
        ):
        self.repo_absolute_path = repo_absolute_path
        self.build_tool = build_tool
        self.api_url = api_url
        self.api_endpoints = api_endpoints
        self.application_type = application_type

    @logger.catch
    def run(self):
        command_args: list[str] = []

        if self.build_tool == BuildToolType.MAVEN:
            if self.application_type == ApplicationType.QUARKUS:
                command_args = ["mvn", "-f", f"{self.repo_absolute_path}/pom.xml", "quarkus:dev", "-Dquarkus.console.color=false"]
            elif self.application_type == ApplicationType.SPRING_BOOT:
                command_args = ["mvn", "-f", f"{self.repo_absolute_path}/pom.xml", "spring-boot:run"]
        
        elif self.build_tool == BuildToolType.GRADLE:
            if self.application_type == ApplicationType.QUARKUS:
                command_args = ["gradle", "-p", self.repo_absolute_path, "quarkusDev"]
            elif self.application_type == ApplicationType.SPRING_BOOT:
                command_args = ["gradle", "-p", self.repo_absolute_path, "bootRun"]

        logger.info(f"Starting application: {self.repo_absolute_path}")

        try:
            self.log_file = open("java_output.log", "w", encoding="utf-8")
            self.log_error = open("java_error_output.log", "w", encoding="utf-8")

            self.process = subprocess.Popen(
                args=command_args,
                stdout=self.log_file,
                stderr=self.log_error,
                text=True
            )

            time.sleep(3)
            status_code = self.process.poll()
            
            if status_code is not None:
                self.close_logs()
                logger.error(f"The Java process failed to start. code={status_code}")
                sys.exit(1)
            
            logger.info("Application Java started.")
            
        except FileNotFoundError:
            self.close_logs()
            logger.error("The executable 'mvn', 'gradle' or 'java' was not found in your system PATH.")
            sys.exit(1)
        except Exception as e:
            self.close_logs()
            logger.error(f"Unexpected error when starting process: {e}")
            sys.exit(1)

    def close_logs(self):
        if self.log_file and not self.log_file.closed:
            self.log_file.close()
        if self.log_error and not self.log_error.closed:
            self.log_error.close()

    def stop(self):
        if hasattr(self, 'process') and self.process:
            logger.info("Stopping Java application...")
            self.process.terminate()
            self.process.wait()
            self.close_logs()
            logger.info("Java application stopped and logs closed.")