from enum import Enum

class BuildToolType(Enum):
	MAVEN = "maven"
	GRADLE = "gradle"
	NONE = "none"