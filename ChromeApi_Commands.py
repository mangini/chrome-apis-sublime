import sublime, sublime_plugin
import os, re
import ChromeApp

def get_samplename_from_file(path):
    match = re.compile(r"^.*\/([^\.\/]+)\.sublime-snippet$").match(path)
    if not match:
        raise Exception("Invalid sample file: %s" % path)
    return match.group(1).replace("_", ".")

def listfiles(dir_name):
    all_files = []
    files = os.listdir(dir_name)
    for path in files:
        full_path = os.path.join(dir_name, path)
        if not path.startswith('.') and not os.path.isdir(full_path):
            all_files.append(full_path)
    return all_files

class new_chrome(sublime_plugin.WindowCommand):
    def run(self, name):
        dir_name = os.path.join(sublime.packages_path(), 
            ChromeApp.PACKAGE_NAME, "snippets", name)
        files = listfiles(dir_name)
        for file in files:
            view = self.window.new_file()
            view.set_name(get_samplename_from_file(file))
            simple_file=re.sub(r".*\/(Packages\/.*)", r"\1", file)
            view.run_command("insert_snippet", {"name": simple_file})

class run_on_chrome(sublime_plugin.WindowCommand):

    def run(self):
        print ("running")
        # /Applications/Google\ Chrome\ Canary.app/Contents/MacOS/Google\ Chrome\ Canary 
        #      --app-id=jligobnedlocadmblphlbchpgoahdagb --no-startup-window


class create_crx(sublime_plugin.WindowCommand):

    def run(self):
        print ("running")
        
