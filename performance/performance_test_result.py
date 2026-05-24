class PerformanceTestResult:
	step: int
	total_requests: int
	success_count: int
	failure_count: int
	average_latency: float
	rps: float
	requests_time: list
	real_duration: float
	difference_latency: float

	def __init__(self):
		pass
