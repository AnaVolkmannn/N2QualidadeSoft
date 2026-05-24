import asyncio
import httpx
import time
from performance.performance_test_result import PerformanceTestResult
from loguru import logger


from core.global_config import GlobalConfig

class PerformanceTest:
    URL: str
    ENDPOINTS: list[str]
    STEPS: list[int]
    STEP_DURATION: int
    REQUEST_INTERVAL_TIME: int
    CONNECTION_RETRY: int
    CONNECTION_RETRY_TIMEOUT: int
    global_config: GlobalConfig
    performance_test_results: list[PerformanceTestResult]

    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config
        self.URL = self.global_config.config["performance"]["api-url"]
        self.ENDPOINTS = self.global_config.config["performance"]["api-endpoints"]
        self.STEPS = self.global_config.config["performance"]["steps"]
        self.STEP_DURATION = self.global_config.config["performance"]["step-duration"]
        self.REQUEST_INTERVAL_TIME = self.global_config.config["performance"]["request-interval-time"]
        self.CONNECTION_RETRY = self.global_config.config["performance"]["connection-retry"]
        self.CONNECTION_RETRY_TIMEOUT = self.global_config.config["performance"]["connection-retry-timeout"]
    
    async def start_tests(self) -> list[PerformanceTestResult]:
        url_to_test = f'http://{self.URL}{self.ENDPOINTS[0]}'
        logger.info(f"Trying to connect [{url_to_test}]")
        self.performance_test_results = []
        
        async with httpx.AsyncClient() as http_client:
            for r in range(self.CONNECTION_RETRY):
                try:
                    if await self.fetch(client=http_client, url=url_to_test, results_list=[]) == -1.0:
                        if r + 1 == self.CONNECTION_RETRY:
                            logger.warning("Unable to connect to the application.")
                            return
                        logger.info(f"Retrying again... ({r + 1}/{self.CONNECTION_RETRY})")
                        await asyncio.sleep(self.CONNECTION_RETRY_TIMEOUT / 1000)
                        continue
                    break
                except (httpx.ConnectError, httpx.HTTPError) as hce:
                    logger.error(f"HTTP exception: {hce}")
                    if r == self.CONNECTION_RETRY - 1:
                        logger.warning("Unable to connect to the application.")
                        return
                    logger.info(f"Retrying again... ({r + 1}/{self.CONNECTION_RETRY})")
                await asyncio.sleep(self.CONNECTION_RETRY_TIMEOUT / 1000)
        
        logger.info("Connection established!")
        for endpoint in self.ENDPOINTS:
            for step in self.STEPS:
                logger.info(f"Testing {step} simultaneous calls to endpoint {endpoint}.")
                try:
                    await self.init_step(step, endpoint)
                except Exception as e:
                    logger.error(f"Error during step test: {e}")
        
        return self.performance_test_results

    async def init_step(self, step: int, endpoint: str):
        url = f"http://{self.URL}{endpoint}"
        
        limits = httpx.Limits(max_connections=10000, max_keepalive_connections=5000)
        timeout = httpx.Timeout(None)
        
        requests_time = []
        step_start_time = time.perf_counter()
        
        try:
            async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
                virtual_users = [
                    self.virtual_user_worker(client, url, requests_time) 
                    for _ in range(step)
                ]
                
                await asyncio.gather(*virtual_users)
                
        except Exception as e:
            logger.error(f"An error occurred in client context: {e}")
            
        real_duration = time.perf_counter() - step_start_time
        
        successes = [t for t in requests_time if t > 0]
        failures = [t for t in requests_time if t == -1.0]
        
        perf_result = PerformanceTestResult()
        perf_result.step = step
        perf_result.total_requests = len(requests_time)
        perf_result.success_count = len(successes)
        perf_result.failure_count = len(failures)
        perf_result.requests_time = requests_time
        perf_result.real_duration = real_duration
        if successes:
            perf_result.average_latency = sum(successes) / len(successes)
            perf_result.rps = len(requests_time) / real_duration

            perf_results_size = len(self.performance_test_results)
            print("RESULTS SIZE: ", perf_results_size)
            if perf_results_size > 0:
                diff_latency = await self.percentage_difference_latency(
                    self.performance_test_results[perf_results_size - 1].average_latency,
                    perf_result.average_latency
                )
                print("DIFF LATENCY: ", diff_latency)
                perf_result.difference_latency = diff_latency
            else:
                perf_result.difference_latency = 0
        

        self.performance_test_results.append(perf_result)

    async def virtual_user_worker(self, client: httpx.AsyncClient, url: str, results_list: list):
        test_end_time = time.perf_counter() + (self.STEP_DURATION / 1000)
        interval_seconds = self.REQUEST_INTERVAL_TIME / 1000
        
        while time.perf_counter() < test_end_time:
            await self.fetch(client, url, results_list)
            await asyncio.sleep(interval_seconds)

    async def fetch(self, client: httpx.AsyncClient, url: str, results_list: list) -> float:
        req_init_time = time.perf_counter_ns()
        try:
            response = await client.get(url)
            _ = response.text 
            
            latency = (time.perf_counter_ns() - req_init_time) / 1_000_000
            results_list.append(latency)
            return latency
        except Exception as e:
            results_list.append(-1.0)
            return -1.0
    
    # Calcula porcentagem em relação a A
    async def percentage_difference_latency(self, a, b):
        print("A: ", a)
        print("B: ", b)
        
        diff = b - a
        percent = diff*100/a
        return percent
