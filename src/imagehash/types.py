"""
Type definitions and imports for imagehash
"""

import sys

try:
	# specify allowed values if possible (py3.8+)
	from typing import Literal

	WhashMode = Literal['haar', 'db4']  # type: ignore
except ImportError:
	WhashMode = str  # type: ignore

try:
	# enable numpy array typing (py3.7+)
	import numpy.typing

	NDArray = numpy.typing.NDArray[numpy.bool_]
except (AttributeError, ImportError):
	NDArray = list  # type: ignore

# type of Callable
if sys.version_info >= (3, 3):
	if sys.version_info >= (3, 9, 0) and sys.version_info <= (3, 9, 1):
		# https://stackoverflow.com/questions/65858528/is-collections-abc-callable-bugged-in-python-3-9-1
		from typing import Callable
	else:
		from collections.abc import Callable
	try:
		from PIL import Image

		MeanFunc = Callable[[NDArray], float]
		HashFunc = Callable[[Image.Image], 'ImageHash']
	except (TypeError, ImportError):
		MeanFunc = Callable  # type: ignore
		HashFunc = Callable  # type: ignore
