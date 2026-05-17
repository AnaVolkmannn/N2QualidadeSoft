import tomllib

class GlobalConfig:
	config_path: str
	config: any
	
	def __init__(self, config_path: str):
		self.config_path = config_path
		
		with open(config_path, "rb") as f:
			self.config = tomllib.load(f)
