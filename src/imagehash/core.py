"""
Core classes for imagehash
"""

from typing import TYPE_CHECKING

import numpy

from imagehash.utils import binary_array_to_hex

if TYPE_CHECKING:
	from imagehash.types import NDArray


class ImageHash:
	"""
	Hash encapsulation. Can be used for dictionary keys and comparisons.
	"""

	def __init__(self, binary_array: 'NDArray') -> None:
		self.hash = binary_array

	def __str__(self) -> str:
		return binary_array_to_hex(self.hash.flatten())

	def __repr__(self) -> str:
		return repr(self.hash)

	def __sub__(self, other: 'ImageHash') -> int:
		if other is None:
			raise TypeError('Other hash must not be None.')
		if self.hash.size != other.hash.size:
			raise TypeError(
				'ImageHashes must be of the same shape.',
				self.hash.shape,
				other.hash.shape,
			)
		return int(numpy.count_nonzero(self.hash.flatten() != other.hash.flatten()))

	def __eq__(self, other):
		# type: (object) -> bool
		if other is None:
			return False
		return numpy.array_equal(self.hash.flatten(), other.hash.flatten())  # type: ignore

	def __ne__(self, other):
		# type: (object) -> bool
		if other is None:
			return False
		return not numpy.array_equal(self.hash.flatten(), other.hash.flatten())  # type: ignore

	def __hash__(self) -> int:
		# this returns a 8 bit integer, intentionally shortening the information
		return sum([2 ** (i % 8) for i, v in enumerate(self.hash.flatten()) if v])

	def __len__(self) -> int:
		# Returns the bit length of the hash
		return self.hash.size


class ImageMultiHash:
	"""
	This is an image hash containing a list of individual hashes for segments of the image.
	The matching logic is implemented as described in Efficient Cropping-Resistant Robust Image Hashing
	"""

	def __init__(self, hashes: list[ImageHash]) -> None:
		self.segment_hashes = hashes

	def __eq__(self, other):
		# type: (object) -> bool
		if other is None:
			return False
		return self.matches(other)  # type: ignore

	def __ne__(self, other):
		# type: (object) -> bool
		return not self.matches(other)  # type: ignore

	def __sub__(self, other: 'ImageMultiHash', hamming_cutoff: float | None = None, bit_error_rate: float | None = None) -> float:
		matches, sum_distance = self.hash_diff(other, hamming_cutoff, bit_error_rate)
		max_difference = len(self.segment_hashes)
		if matches == 0:
			return max_difference
		max_distance = matches * len(self.segment_hashes[0])
		tie_breaker = 0 - (float(sum_distance) / max_distance)
		match_score = matches + tie_breaker
		return max_difference - match_score

	def __hash__(self) -> int:
		return hash(tuple(hash(segment) for segment in self.segment_hashes))

	def __str__(self) -> str:
		return ','.join(str(x) for x in self.segment_hashes)

	def __repr__(self) -> str:
		return repr(self.segment_hashes)

	def hash_diff(self, other_hash: 'ImageMultiHash', hamming_cutoff: float | None = None, bit_error_rate: float | None = None) -> tuple[int, int]:
		"""
		Gets the difference between two multi-hashes, as a tuple. The first element of the tuple is the number of
		matching segments, and the second element is the sum of the hamming distances of matching hashes.
		NOTE: Do not order directly by this tuple, as higher is better for matches, and worse for hamming cutoff.
		:param other_hash: The image multi hash to compare against
		:param hamming_cutoff: The maximum hamming distance to a region hash in the target hash
		:param bit_error_rate: Percentage of bits which can be incorrect, an alternative to the hamming cutoff. The
		default of 0.25 means that the segment hashes can be up to 25% different
		"""
		# Set default hamming cutoff if it's not set.
		if hamming_cutoff is None:
			if bit_error_rate is None:
				bit_error_rate = 0.25
			hamming_cutoff = len(self.segment_hashes[0]) * bit_error_rate
		# Get the hash distance for each region hash within cutoff
		distances = []
		for segment_hash in self.segment_hashes:
			lowest_distance = min(
				segment_hash - other_segment_hash
				for other_segment_hash in other_hash.segment_hashes
			)
			if lowest_distance > hamming_cutoff:
				continue
			distances.append(lowest_distance)
		return len(distances), sum(distances)

	def matches(
		self, other_hash: 'ImageMultiHash', region_cutoff: int = 1, hamming_cutoff: float | None = None, bit_error_rate: float | None = None
	) -> bool:
		"""
		Checks whether this hash matches another crop resistant hash, `other_hash`.
		:param other_hash: The image multi hash to compare against
		:param region_cutoff: The minimum number of regions which must have a matching hash
		:param hamming_cutoff: The maximum hamming distance to a region hash in the target hash
		:param bit_error_rate: Percentage of bits which can be incorrect, an alternative to the hamming cutoff. The
		default of 0.25 means that the segment hashes can be up to 25% different
		"""
		matches, _ = self.hash_diff(other_hash, hamming_cutoff, bit_error_rate)
		return matches >= region_cutoff

	def best_match(self, other_hashes: list['ImageMultiHash'], hamming_cutoff: float | None = None, bit_error_rate: float | None = None) -> 'ImageMultiHash':
		"""
		Returns the hash in a list which is the best match to the current hash
		:param other_hashes: A list of image multi hashes to compare against
		:param hamming_cutoff: The maximum hamming distance to a region hash in the target hash
		:param bit_error_rate: Percentage of bits which can be incorrect, an alternative to the hamming cutoff.
		Defaults to 0.25 if unset, which means the hash can be 25% different
		"""
		return min(
			other_hashes,
			key=lambda other_hash: self.__sub__(
				other_hash, hamming_cutoff, bit_error_rate
			),
		)
