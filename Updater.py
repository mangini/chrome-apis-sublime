import json, os, re, urllib, time, sys, traceback, cPickle

API_SIMPLIFIER = re.compile('chrome\.(?:experimental\.)?(.*)')

# Periodically we ping this url below to check if there is an
# updated API. If there is, we download it and re-generate the 
# API object to be used by the extension

UPDATE_URL = "http://chrome-api.storage.googleapis.com/"
FREQUENCY_OF_CHECK = 60*60*24    # measured in seconds, currently 1 day
FILECHANGE_CONTROL_URL = UPDATE_URL + "last_file_change.json"
APPS_API_URL = UPDATE_URL + "apps_latest.json"
EXTENSIONS_API_URL = UPDATE_URL + "extensions_latest.json"

def debug(obj):
	print('[ChromeAppUpdater] %s' % obj)
	if isinstance(obj, Exception):
		traceback.print_exc(file=sys.stdout)

class Updater():

	def __init__(self, myPath):

		self.APPS_FILENAME="%s/apps.json" % myPath
		self.EXTENSIONS_FILENAME="%s/extensions.json" % myPath
		self.UPDATE_CONTROL_FILENAME="%s/lastupdate.json" % myPath

	def clearChecks(self):
		self.fileChangedInfo={}
		

	def readLastUpdateInfo(self):
		try:
			self.updateControl=json.load(open(self.UPDATE_CONTROL_FILENAME, "r"))
		except Exception, e:
			self.updateControl={}
		if type(self.updateControl)!=dict or 'lastCheck' not in self.updateControl:
			self.updateControl={'lastCheck': 0, 'lastUpdate': {'apps_json': 0, 'extensions_json': 0}}


	def updateRequired(self, force=True):
		nowms=time.time()
		
		# only remotely check once a day
		if not force and (nowms-self.updateControl['lastCheck']) < FREQUENCY_OF_CHECK:
			return {'apps': False, 'extensions': False}

		# if it is time to check, let's also see if the remote files have changed:
		self.fileChangedInfo = json.loads(urllib.urlopen(
			FILECHANGE_CONTROL_URL).read())

		if type(self.fileChangedInfo)!=dict or 'apps_json' not in self.fileChangedInfo:
			raise Exception("invalid format of "+FILECHANGE_CONTROL_URL)

		appsNeeds=self.fileChangedInfo['apps_json']!=self.updateControl['lastUpdate']['apps_json']
		extensionsNeeds=self.fileChangedInfo['extensions_json']!=self.updateControl['lastUpdate']['extensions_json']
		return {'apps': appsNeeds, 'extensions': extensionsNeeds}


	def processApiJson(self, inputUrl, outputFilename):
		completions = []

		obj = json.loads(urllib.urlopen(inputUrl).read())
		for api in obj:
			debug("on processApiJson!: api %s" % api)
			if 'functions' in obj[api]:
				simpleApiName=API_SIMPLIFIER.match(api).groups(0)[0]
				for method in obj[api]['functions']:
					paramStr=""
					if 'parameters' in method:
						for param in method['parameters']:
							paramStr+=param['name']
							if 'last' not in param or not param['last']:
								paramStr+=", "
					completion=(
						"%s.%s" % (api, method['name']),
						"%s\tChrome %s" % (method['name'], simpleApiName), 
						"%s.%s(%s)" % (api, method['name'], paramStr))
					completions.append(completion)
		with open(outputFilename, 'w') as out:
			cPickle.dump(completions, out)

	def filesUpdated(self):
		self.updateControl={'lastCheck': time.time(), 
			'lastUpdate': {'apps_json': self.fileChangedInfo['apps_json'], 
				'extensions_json': self.fileChangedInfo['extensions_json']}}	
		with open(self.UPDATE_CONTROL_FILENAME, 'w') as out:
			json.dump(self.updateControl, out)

	def run(self, force=False):

		self.clearChecks()
		try:
			self.readLastUpdateInfo()
			needsUpdate = self.updateRequired(force)
			changesCommited = False

			if needsUpdate['apps']:
				self.processApiJson(APPS_API_URL, self.APPS_FILENAME)
				changesCommited = True

			if needsUpdate['extensions']:
				self.processApiJson(EXTENSIONS_API_URL, self.EXTENSIONS_FILENAME)
				changesCommited = True

			if changesCommited: self.filesUpdated()

		except Exception, e:
			debug("Could not update API")
			debug(e)


def main(argv=[None]):
	force=False
	if len(argv)>0:
		force= (argv[0]=="force")
	u = Updater(".")
	u.run(force);

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

