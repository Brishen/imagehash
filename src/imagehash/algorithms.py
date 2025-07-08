"""
Hash algorithms for imagehash
"""

import numpy
from PIL import Image, ImageFilter
from imagehash.core import ImageHash, ImageMultiHash
from imagehash.types import MeanFunc, HashFunc
from imagehash.utils import ANTIALIAS, _find_all_segments


def average_hash(image, hash_size=8, mean=numpy.mean):
	# type: (Image.Image, int, MeanFunc) -> ImageHash
	"""
	Average Hash computation

	Implementation follows https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

	Step by step explanation: https://web.archive.org/web/20171112054354/https://www.safaribooksonline.com/blog/2013/11/26/image-hashing-with-python/ # noqa: E501

	@image must be a PIL instance.
	@mean how to determine the average luminescence. can try numpy.median instead.
	"""
	if hash_size < 2:
		raise ValueError('Hash size must be greater than or equal to 2')

	# reduce size and complexity, then convert to grayscale
	image = image.convert('L').resize((hash_size, hash_size), ANTIALIAS)

	# find average pixel value; 'pixels' is an array of the pixel values, ranging from 0 (black) to 255 (white)
	pixels = numpy.asarray(image)
	avg = mean(pixels)

	# create string of bits
	diff = pixels > avg
	# make a hash
	return ImageHash(diff)


def phash(image, hash_size=8, highfreq_factor=4):
	# type: (Image.Image, int, int) -> ImageHash
	"""
	Perceptual Hash computation.

	Implementation follows https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

	@image must be a PIL instance.
	"""
	if hash_size < 2:
		raise ValueError('Hash size must be greater than or equal to 2')

	import scipy.fftpack
	img_size = hash_size * highfreq_factor
	image = image.convert('L').resize((img_size, img_size), ANTIALIAS)
	pixels = numpy.asarray(image)
	dct = scipy.fftpack.dct(scipy.fftpack.dct(pixels, axis=0), axis=1)
	dctlowfreq = dct[:hash_size, :hash_size]
	med = numpy.median(dctlowfreq)
	diff = dctlowfreq > med
	return ImageHash(diff)


def phash_simple(image, hash_size=8, highfreq_factor=4):
	# type: (Image.Image, int, int) -> ImageHash
	"""
	Perceptual Hash computation.

	Implementation follows https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html

	@image must be a PIL instance.
	"""
	import scipy.fftpack
	img_size = hash_size * highfreq_factor
	image = image.convert('L').resize((img_size, img_size), ANTIALIAS)
	pixels = numpy.asarray(image)
	dct = scipy.fftpack.dct(pixels)
	dctlowfreq = dct[:hash_size, 1:hash_size + 1]
	avg = dctlowfreq.mean()
	diff = dctlowfreq > avg
	return ImageHash(diff)


def dhash(image, hash_size=8):
	# type: (Image.Image, int) -> ImageHash
	"""
	Difference Hash computation.

	following https://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

	computes differences horizontally

	@image must be a PIL instance.
	"""
	# resize(w, h), but numpy.array((h, w))
	if hash_size < 2:
		raise ValueError('Hash size must be greater than or equal to 2')

	image = image.convert('L').resize((hash_size + 1, hash_size), ANTIALIAS)
	pixels = numpy.asarray(image)
	# compute differences between columns
	diff = pixels[:, 1:] > pixels[:, :-1]
	return ImageHash(diff)


def dhash_vertical(image, hash_size=8):
	# type: (Image.Image, int) -> ImageHash
	"""
	Difference Hash computation.

	following https://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html

	computes differences vertically

	@image must be a PIL instance.
	"""
	# resize(w, h), but numpy.array((h, w))
	image = image.convert('L').resize((hash_size, hash_size + 1), ANTIALIAS)
	pixels = numpy.asarray(image)
	# compute differences between rows
	diff = pixels[1:, :] > pixels[:-1, :]
	return ImageHash(diff)


def whash(image, hash_size=8, image_scale=None, mode='haar', remove_max_haar_ll=True):
	# type: (Image.Image, int, int | None, str, bool) -> ImageHash
	"""
	Wavelet Hash computation.

	based on https://www.kaggle.com/c/avito-duplicate-ads-detection/

	@image must be a PIL instance.
	@hash_size must be a power of 2 and less than @image_scale.
	@image_scale must be power of 2 and less than image size. By default is equal to max
					power of 2 for an input image.
	@mode (see modes in pywt library):
					'haar' - Haar wavelets, by default
					'db4' - Daubechies wavelets
	@remove_max_haar_ll - remove the lowest low level (LL) frequency using Haar wavelet.
	"""
	import pywt
	if image_scale is not None:
		assert image_scale & (image_scale - 1) == 0, 'image_scale is not power of 2'
	else:
		image_natural_scale = 2**int(numpy.log2(min(image.size)))
		image_scale = max(image_natural_scale, hash_size)

	ll_max_level = int(numpy.log2(image_scale))

	level = int(numpy.log2(hash_size))
	assert hash_size & (hash_size - 1) == 0, 'hash_size is not power of 2'
	assert level <= ll_max_level, 'hash_size in a wrong range'
	dwt_level = ll_max_level - level

	image = image.convert('L').resize((image_scale, image_scale), ANTIALIAS)
	pixels = numpy.asarray(image) / 255.

	# Remove low level frequency LL(max_ll) if @remove_max_haar_ll using haar filter
	if remove_max_haar_ll:
		coeffs = pywt.wavedec2(pixels, 'haar', level=ll_max_level)
		coeffs = list(coeffs)
		coeffs[0] *= 0
		pixels = pywt.waverec2(coeffs, 'haar')

	# Use LL(K) as freq, where K is log2(@hash_size)
	coeffs = pywt.wavedec2(pixels, mode, level=dwt_level)
	dwt_low = coeffs[0]

	# Subtract median and compute hash
	med = numpy.median(dwt_low)
	diff = dwt_low > med
	return ImageHash(diff)


def colorhash(image, binbits=3):
	# type: (Image.Image, int) -> ImageHash
	"""
	Color Hash computation.

	Computes fractions of image in intensity, hue and saturation bins:

	* the first binbits encode the black fraction of the image
	* the next binbits encode the gray fraction of the remaining image (low saturation)
	* the next 6*binbits encode the fraction in 6 bins of saturation, for highly saturated parts of the remaining image
	* the next 6*binbits encode the fraction in 6 bins of saturation, for mildly saturated parts of the remaining image

	@binbits number of bits to use to encode each pixel fractions
	"""

	# bin in hsv space:
	intensity = numpy.asarray(image.convert('L')).flatten()
	h, s, v = [numpy.asarray(v).flatten() for v in image.convert('HSV').split()]
	# black bin
	mask_black = intensity < 256 // 8
	frac_black = mask_black.mean()
	# gray bin (low saturation, but not black)
	mask_gray = s < 256 // 3
	frac_gray = numpy.logical_and(~mask_black, mask_gray).mean()
	# two color bins (medium and high saturation, not in the two above)
	mask_colors = numpy.logical_and(~mask_black, ~mask_gray)
	mask_faint_colors = numpy.logical_and(mask_colors, s < 256 * 2 // 3)
	mask_bright_colors = numpy.logical_and(mask_colors, s > 256 * 2 // 3)

	c = max(1, mask_colors.sum())
	# in the color bins, make sub-bins by hue
	hue_bins = numpy.linspace(0, 255, 6 + 1)
	if mask_faint_colors.any():
		h_faint_counts, _ = numpy.histogram(h[mask_faint_colors], bins=hue_bins)
	else:
		h_faint_counts = numpy.zeros(len(hue_bins) - 1)
	if mask_bright_colors.any():
		h_bright_counts, _ = numpy.histogram(h[mask_bright_colors], bins=hue_bins)
	else:
		h_bright_counts = numpy.zeros(len(hue_bins) - 1)

	# now we have fractions in each category (6*2 + 2 = 14 bins)
	# convert to hash and discretize:
	maxvalue = 2**binbits
	values = [min(maxvalue - 1, int(frac_black * maxvalue)), min(maxvalue - 1, int(frac_gray * maxvalue))]
	for counts in list(h_faint_counts) + list(h_bright_counts):
		values.append(min(maxvalue - 1, int(counts / c * maxvalue)))
	# print(values)
	bitarray = []
	for v in values:
		bitarray += [v // (2**(binbits - i - 1)) % 2**(binbits - i) > 0 for i in range(binbits)]
	return ImageHash(numpy.asarray(bitarray).reshape((-1, binbits)))


def crop_resistant_hash(
	image,  # type: Image.Image
	hash_func=dhash,  # type: HashFunc
	limit_segments=None,  # type: int | None
	segment_threshold=128,  # type: int
	min_segment_size=500,  # type: int
	segmentation_image_size=300  # type: int
):
	# type: (...) -> ImageMultiHash
	"""
	Creates a CropResistantHash object, by the algorithm described in the paper "Efficient Cropping-Resistant Robust
	Image Hashing". DOI 10.1109/ARES.2014.85
	This algorithm partitions the image into bright and dark segments, using a watershed-like algorithm, and then does
	an image hash on each segment. This makes the image much more resistant to cropping than other algorithms, with
	the paper claiming resistance to up to 50% cropping, while most other algorithms stop at about 5% cropping.

	Note: Slightly different segmentations are produced when using pillow version 6 vs. >=7, due to a change in
	rounding in the greyscale conversion. This leads to a slightly different result.
	:param image: The image to hash
	:param hash_func: The hashing function to use
	:param limit_segments: If you have storage requirements, you can limit to hashing only the M largest segments
	:param segment_threshold: Brightness threshold between hills and valleys. This should be static, putting it between
	peak and through dynamically breaks the matching
	:param min_segment_size: Minimum number of pixels for a hashable segment
	:param segmentation_image_size: Size which the image is resized to before segmentation
	"""

	orig_image = image.copy()
	# Convert to gray scale and resize
	image = image.convert('L').resize((segmentation_image_size, segmentation_image_size), ANTIALIAS)
	# Add filters
	image = image.filter(ImageFilter.GaussianBlur()).filter(ImageFilter.MedianFilter())
	pixels = numpy.array(image).astype(numpy.float32)

	segments = _find_all_segments(pixels, segment_threshold, min_segment_size)

	# If there are no segments, have 1 segment including the whole image
	if not segments:
		full_image_segment = {(0, 0), (segmentation_image_size - 1, segmentation_image_size - 1)}
		segments.append(full_image_segment)

	# If segment limit is set, discard the smaller segments
	if limit_segments:
		segments = sorted(segments, key=lambda s: len(s), reverse=True)[:limit_segments]

	# Create bounding box for each segment
	hashes = []
	for segment in segments:
		orig_w, orig_h = orig_image.size
		scale_w = float(orig_w) / segmentation_image_size
		scale_h = float(orig_h) / segmentation_image_size
		min_y = min(coord[0] for coord in segment) * scale_h
		min_x = min(coord[1] for coord in segment) * scale_w
		max_y = (max(coord[0] for coord in segment) + 1) * scale_h
		max_x = (max(coord[1] for coord in segment) + 1) * scale_w
		# Compute robust hash for each bounding box
		bounding_box = orig_image.crop((min_x, min_y, max_x, max_y))
		hashes.append(hash_func(bounding_box))
		# Show bounding box
		# im_segment = image.copy()
		# for pix in segment:
		# 	im_segment.putpixel(pix[::-1], 255)
		# im_segment.show()
		# bounding_box.show()

	return ImageMultiHash(hashes)
