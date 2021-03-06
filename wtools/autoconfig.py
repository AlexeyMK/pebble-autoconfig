#!/usr/bin/env python
# encoding: utf-8

import os
import json
import inspect
import collections

from waflib import TaskGen, Task, Node
from waflib.TaskGen import extension, before_method,feature
from waflib.Configure import conf

# jinja2 filter
import re
def cvarname(name):
	"""Convert a string to a valid c variable name (remove space,commas,slashes/...)."""
	return re.sub(r'[^\w\s]', '_', name)
filters = {'max' : max, 'cvarname' : cvarname}

class autoconfig(Task.Task):
	color   = 'PINK'

	def run(self):
		"""Render jinja template."""
		from jinja2 import Environment
		from jinja2 import FileSystemLoader
		
		rootdir = self.generator.path.abspath()
		tpldir = os.path.dirname(self.inputs[0].abspath())
		tpl = os.path.basename(self.inputs[0].abspath())
		
		env = Environment(loader = FileSystemLoader([rootdir, tpldir]), trim_blocks=False)

		#add custom filter
		for filterName, filterFun in filters.iteritems():
			env.filters[filterName] = filterFun
	
		template = env.get_template(tpl)

		# AMK hack: concatenate user's native pebble-js-app.js
		if tpl == "pebble-js-app.js.jinja":
			original_app_js = os.path.join(tpldir,
				"..", "..", "..", "src", "js", "pebble-js-app.js")
			try:
				original_js_contents = open(original_app_js, 'r').read()
				self.appinfo["original_js_contents"] = original_js_contents
			except IOError:
				print "User custom JS not found"

		f = open(self.outputs[0].abspath(), 'w')
		f.write(template.render(self.appinfo))
		f.close()

def configure(conf):
	""" detect jinja installation """
	#load jinja module
	#conf.check_python_module('jinja2')
	try:
		from jinja2 import Environment
		from jinja2 import FileSystemLoader
	except Exception, e:
		conf.fatal("Jinja template engine is not available! (" + e.message + ")")

def build(bld):
	jinjapath = os.path.dirname(inspect.getfile(inspect.currentframe()))
	jinjapath = os.path.join(jinjapath, 'templates/*.jinja')
	for template in bld.path.ant_glob([jinjapath]):
		bld.add_manual_dependency(
			template,
			bld.path.find_node('appinfo.json'))
			
@extension('.jinja')
def process_autoconfig(self, node):	
	out = node.change_ext('')

	out = Node.split_path(out.abspath())[-1]

	appinfo_content=open('appinfo.json')
	appinfo_json=json.load(appinfo_content,object_pairs_hook=collections.OrderedDict)

	out = self.bld.path.find_or_declare([str(out)])

	tsk = self.create_task('autoconfig', [node], [out])
	tsk.appinfo = appinfo_json

	if out.suffix() in ['.c']:
		self.source.append(out)

@feature('autoconf')
@before_method("process_source")
def fprocess_autoconfig(self):
	jinjapath = os.path.dirname(inspect.getfile(inspect.currentframe()))
	jinjapath = os.path.join(jinjapath, 'templates/*.jinja')
	for src in self.path.ant_glob([jinjapath]):
		self.process_autoconfig(src)


@conf
def pbl_autoconfprogram(self,*k,**kw):
	kw['features']='c cprogram autoconf'
	return self(*k,**kw)
