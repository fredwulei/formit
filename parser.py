#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import hashlib
import random
import packages
import sys


class Option:
	def __init__(self, label, parent_label, type, checked):
		self.label = label
		self.name = label.lower()
		self.parent_label = parent_label
		self.type = type
		self.checked = checked

	def to_html(self):
		if self.type in ('radio','checkbox'):
			if self.checked:
				return '<input type="%s" name="%s" value="%s" checked> %s ' % (self.type, self.parent_label.lower(), self.name, self.label)
			else:
				return '<input type="%s" name="%s" value="%s"> %s ' % (self.type, self.parent_label.lower(), self.name, self.label)
		elif self.type in ('select',):
			return '<option value="%s">%s</option>' % (self.label.lower(), self.label)
		else:
			return ''

class Field:

	option_patterns = {
		'radio': r'\(([\* ])\)\s*([^\(]+)\s*',
		'checkbox': r'\[([x ])\]\s*([^\[]+)\s*',
		'select': r'\|\s*([^\(][^\|]+)',
	}

	def __init__(self, label, type, content, placeholder=''):
		self.label = label
		self.type = type
		self.placeholder = placeholder.strip()
		tmp = ''.join(e for e in label if e.isalnum() or e == ' ')
		self.name = '-'.join(label.lower().split())
		self.options = []
		if type in ('radio', 'checkbox', 'select'):
			self.get_options(content)

	def __str__(self):
		return '%s @ %s' % (self.label, self.type)

	def __repr__(self):
		return self.__str__()


	def get_options(self,content):
		pattern = Field.option_patterns[self.type]
		for label in re.findall(pattern, content):
			
			if self.type in ('radio', 'checkbox'):
				option_label = label[1]
				is_selected = label[0]!=' '
				# o = Option(label[1], self.label, self.type, label[0]!=' ')
			else:
				option_label = label
				is_selected = False
				# print label
				# print '-'*42

			opts = self.render_package(option_label)
			for opt in opts:
				o = Option(opt, self.label, self.type, is_selected)
				self.options.append(o)


	def render_package(self, label):
		package_pattern = r"@\'([\w_\d\.]+)\'((?:<<|>>|><|<>)?)"
		match = re.match(package_pattern,label)
		if match:
			part1 = match.group(1)
			part2 = match.group(2)
			arr = []
			if '..' not in part1:
				print part1
				package_name = part1 # remove "'" around the package_name
				if package_name in packages.packages:
					package = packages.packages[package_name]
					for item in package:
						arr.append(item)
			else:
				num1, num2 = part1.split('..')
				for n in xrange(int(num1),int(num2)+1):
					arr.append(str(n))
		

			if len(arr) == 0:
				return [label,]


			if part2 == '<<':  # ascending
				return sorted(arr)
			elif part2 == '>>':  # descending
				return sorted(arr,reverse=True)
			elif part2 in ('<>', '><',): # random shuffle
				random.shuffle(arr)
				return arr
			else:
				return arr
		else:
			return [label,]


	def to_html(self):

		options_html = [o.to_html() for o in self.options]
		attrs = []
		if self.placeholder != '':
			attr = 'placeholder="%s"' % self.placeholder
			attrs.append(attr)
		if self.type in ('text', 'password'):
			return '<label>%s</label><input type="%s" name="%s" %s>' % (self.label, self.type, self.name, ' '.join(attrs))
		elif self.type in ('radio', 'checkbox'):
			return '<label>%s</label>%s' % (self.label, ''.join(options_html))
		elif self.type in ('select',):
			if self.placeholder != '':
				placeholder_option = '<option value="" disabled selected>%s</option>\n' % self.placeholder
			else:
				placeholder_option = ''
			return '<label>%s</label>\n<select name="%s">\n%s%s\n</select>' % (self.label, self.name, placeholder_option, '\n'.join(options_html))
		elif self.type in ('textarea',):
			return '<label>%s</label>\n<textarea name="%s" rows="2" cols="30" %s></textarea>\n' % (self.label, self.name, ' '.join(attrs))
		else:
			return ''

	def wrapper(self, wrapper_type='p'):
		if wrapper_type == 'p':
			return '<p>%s</p>' % self.to_html()
		elif wrapper_type == 'no':
			return  self.to_html()
		elif wrapper_type == 'div':
			return  '<div>%s</div>' % self.to_html()
		else:
			return self.to_html()

class PlainText:
	def __init__(self, content, use_wrapper=True):
		self.content = content
		self.use_wrapper = use_wrapper

	def __str__(self):
		return self.content

	def __repr__(self):
		return self.__str__()

	def to_html(self):
		return self.content

	def wrapper(self, wrapper_type='p'):
		if self.use_wrapper:
			if wrapper_type == 'p':
				return '<p>%s</p>' % self.to_html()
			elif wrapper_type == 'no':
				return  self.to_html()
			elif wrapper_type == 'div':
				return  '<div>%s</div>' % self.to_html()
			else:
				return self.to_html()
		else:
			return self.to_html()

class Form:

	patterns = (
		('password', r"^(.+?):\s*(\[\s*(\*{3,})\s*\])\s*$"), # Password: [ **** ]
		('text', r"^(.+?):\s*(\[\s*([^\]]*?)\s*\])\s*$"), # Text: [ Support Placeholder ]
		('radio', r"^(.+?):\s*((?:\([\* ]\)\s*[^\(]+\s*)+)\s*$"), # Radio: (*) Selected ( ) Not Selected
		('checkbox', r"^(.+?):\s*((?:\[[x ]\]\s*[^\[]+\s*)+)\s*$"), # Checkbox [x] Checked [ ] Not [ ] Neither
		('select', r"^(.+?):\s*(\|(?:\s*\(([^\)]*?)\s*\)\s*\|)?(?:[^\|]*\|)+)\s*$"), #
		('textarea', r"^(.+?):\s*\s*(\{\s*([^\]]*?)\s*\}\d*)\s*$"),
		('fieldset_start', r"^-+([\w ]+)-{3,}$"),
		('fieldset_end', r"^-{3,}$")
		)

	escape_chars = ':@#*()[]{}\'\\|'
	rand_str = 'formit'
	escape_str_len = 16
	comment_char = '`'

	def __init__(self, file_path, output_path, title="Form", theme=""):
		self.title = title
		self.file_path = file_path
		self.output_path = output_path
		self.fields = []
		self.lines = []
		
		self.escape_out_dict = {}
		self.escape_in_dict = {}
		self.separator = ''
		self.init_escape()
		self.next_page = ''
		if theme == 'bootstrap':
			self.theme = '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" \
			integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">'
		else:
			self.theme = ''
		self.parse()



	def parse(self):
		file = open(self.file_path, 'r')
		for raw_line in file:
			line = self.process_line(raw_line)
			if len(line) == 0:
				continue
			pattern_found = False
			for pair in Form.patterns:
				key = pair[0]
				pattern = pair[1]
				match = re.search(pattern, line)
				if match:
					pattern_found = True
					if key == 'fieldset_start':
						s = '<fieldset>\n<legend>%s</legend>' % match.group(1)
						pt = PlainText(s, False)
						self.lines.append(pt)
						continue
					if key == 'fieldset_end':
						pt = PlainText('</fieldset>', False)
						self.lines.append(pt)
						continue

					label = match.group(1)
					content = match.group(2)
					if key in ('text', 'textarea','select',):
						placeholder = match.group(3)
						if placeholder == None:
							placeholder = ''
						f = Field(label, key, content,placeholder)
					elif key in ('password',):
						f = Field(label, key, content)
					else:
						f = Field(label,key, content)
					self.fields.append(f)
					self.lines.append(f)
					
					break
			if not pattern_found:
				pt = PlainText(line)
				self.lines.append(pt)
		file.close()



	
	def init_escape(self):
		self.separator = hashlib.sha224(Form.rand_str).hexdigest()[:Form.escape_str_len]
		for c in Form.escape_chars:
			hash_str = hashlib.sha224(c+Form.rand_str).hexdigest()[:Form.escape_str_len]
			self.escape_out_dict[c] = hash_str
			self.escape_in_dict[hash_str] = c

	def escape_out(self,s):
		if len(s) <= 1:
			return s
		l = list(s)
		for i in xrange(len(l)-1):
			if l[i] == '\\' and l[i+1] in Form.escape_chars:
				l[i] = self.separator
				l[i+1] = self.escape_out_dict[l[i+1]]
		return ''.join(l)

	def escape_in(self,s):
		l = s.split(self.separator)
		for i in xrange(len(l)):
			p = l[i][:Form.escape_str_len]
			if p in self.escape_in_dict:
				l[i] = self.escape_in_dict[p]+l[i][Form.escape_str_len:]
		return ''.join(l)

	def remove_comment(self,s):
		return s.split(Form.comment_char)[0]

	def process_line(self, line):
		return self.remove_comment(self.escape_out(line.rstrip()))

	def to_html(self):
		htmls = [self.escape_in(l.wrapper()) for l in self.lines]
		return '\n'.join(htmls)

	def wrapper(self):
		# return '<!DOCTYPE html>\n<head>\n<title>%s</title>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n</head>\n<body>\n%s\n</body>\n</html>' % (self.title, 
			# self.to_html())
		return self.to_html()

	def generate(self):
		# file = open(self.output_path,'w')
		s = self.wrapper()
		# file.write(s)
		# file.close()
		print s


if __name__ == "__main__":
	input_path = sys.argv[1]
	# output_path = sys.argv[2]
	output_path = input_path+'.html'
	# form = Form('test.formit', 'output.html')
	form = Form(input_path, output_path)
	form.generate()

