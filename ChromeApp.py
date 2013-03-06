import sublime, sublime_plugin
import json, os, re, cPickle

API_SIMPLIFIER=re.compile('chrome\.(?:experimental\.)?(.*)')
PACKAGE_NAME = "Chrome Apps and Extensions"

MANIFEST_LOOKSLIKE_NOTHING=0
MANIFEST_LOOKSLIKE_APP=1
MANIFEST_LOOKSLIKE_EXTENSION=2

def debug(obj):
	print('[ChromeApp] %s' % obj)

# search parent dirs for manifest:
def findProjectRoot(baseDir):
	while True:
		manifestName= "%s%smanifest.json" % ( baseDir, os.sep )
		if os.path.isfile(manifestName):
			return baseDir
			
		parent = os.path.dirname(baseDir)
		if parent == baseDir:
			# search got to the root dir
			return None

		baseDir = parent

	return None


class ChromeApp(sublime_plugin.EventListener):

	def __init__(self):
		debug("initiating EventListener!")
		self.activeInViews={}
		self.manifestForOpenViews={}
		self.appsCompletions=cPickle.load(open("%s%s%s%sapps.json" % 
			(sublime.packages_path(), os.sep, PACKAGE_NAME, os.sep), 'r'))
		self.extensionsCompletions=cPickle.load(open("%s%s%s%sextensions.json" % 
			(sublime.packages_path(), os.sep, PACKAGE_NAME, os.sep), 'r'))
		#debug(self.appsCompletions)

	def activateForView(self, view, manifestName, appType):
		self.activeInViews[view.id()] = appType
		self.manifestForOpenViews[view.id()] = manifestName
		status = "Chrome Packaged App" if appType==MANIFEST_LOOKSLIKE_APP else "Chrome Extension"
		view.set_status("ChromeApp", status)
		debug("activated for view %s as type %s - manifest found at %s" % 
			(view.file_name(), appType, manifestName))

	def deactivateForView(self, view):
		if view.id() in self.activeInViews:
			del self.activeInViews[view.id()]
		if view.id() in self.manifestForOpenViews:
			del self.manifestForOpenViews[view.id()]
		view.erase_status("ChromeApp")
		debug("deactivated for view %s" % view.file_name())

	def check_view(self, view, force=False):
		debug("checking (force=%s) %s" % (force, view.file_name()))
		if view.file_name() == None or view.id() == None:
			return False

		if not force and view.id() in self.activeInViews:
			return self.activeInViews[view.id()]

		if view.file_name().endswith(".js"):
			parentDir = findProjectRoot(view.file_name())
			if (parentDir != None):
				manifestName= "%s%smanifest.json" % (parentDir, os.sep)
				looksLike = self.processManifest(manifestName)
				if looksLike != MANIFEST_LOOKSLIKE_NOTHING:
					self.activateForView(view, manifestName, looksLike)
					return True

		self.deactivateForView(view)
		return False

	def processManifest(self, path):
		try:
			obj = json.load(open(path, 'r'))
			if not 'name' in obj:
				return MANIFEST_LOOKSLIKE_NOTHING
			if 'app' in obj and 'background' in obj['app']:
				return MANIFEST_LOOKSLIKE_APP
			else:
				return MANIFEST_LOOKSLIKE_EXTENSION

		except Exception, e:
			debug(e)
			return MANIFEST_LOOKSLIKE_NOTHING

	def on_close(self, view):
		self.deactivateForView(view)

	def on_post_save(self, view):
		debug("on_post_save, view="+view.file_name())
		if not self.check_view(view):
			if os.path.basename(view.file_name()) == "manifest.json":
				# for each opened view, let's check if they are in the 
				# same project of this manifest just saved
				for viewId in self.manifestForOpenViews:
					debug("manifest saved, rechecking open files: %s %s" % (viewId, self.manifestForOpenViews[viewId]))
					if self.manifestForOpenViews[viewId] == view.file_name:
						# force view recheck
						self.check_view(v, True, False)

#				views=view.window().views()
#				for v in views:
#					self.check_view(v, True)

	def on_load(self, view):
		self.check_view(view)

	def on_query_completions(self, view, prefix, locations):
		if view.id() in self.activeInViews:
			if self.activeInViews[view.id()]==MANIFEST_LOOKSLIKE_APP:
				return self.appsCompletions
			else:
				return self.extensionsCompletions
		  #completions = []
#		  return [('isochronousTransfer\tChrome usb', 'chrome.experimental.usb.isochronousTransfer(callback)')]
#		  return [('chrome.experimental.usb.isochronousTransfer', 'isochronousTransfer\tChrome usb', 'chrome.experimental.usb.isochronousTransfer(callback)')]


