import os
import re

import six


def test_run():
	# test code in README.md file
	# find any chunks in python code blocks
	# which code lines, which start with >>>
	parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
	with open(os.path.join(parent_dir, 'README.md')) as f:
		content = f.read()
	
	# Extract Python code blocks
	python_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)
	
	# Extract lines that start with >>>
	chunk = []
	for block in python_blocks:
		lines = block.split('\n')
		for line in lines:
			if line.startswith('>>> '):
				chunk.append(line[4:] + '\n')  # Remove '>>> ' prefix

	code = ''.join(chunk)
	print("running::\n" + code)
	print("result:", six.exec_(code, {}, {}))
