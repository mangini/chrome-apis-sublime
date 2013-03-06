import sublime
import sublime_plugin
import re
import os
import ChromeApp

CSP_VIOLATIONS_SYNTAX = "cspvalidator%sCSPViolations.hidden.tmLanguage" % os.sep
CSP_VIOLATIONS_NAME = "Violations of CSP rules"

class CSPRule():
    """ Represents a validation rule """
    rule = None
    message = None
    setting = None

    def __init__(self, rule, message, setting=None):
        self.rule = re.compile(rule, re.MULTILINE | re.IGNORECASE)
        self.message = message
        self.setting = setting


class CSPError:
    """ Represents an error """
    filename = None
    message = ''
    line = 0

    def __init__(self, filename, line, message):
        self.filename = filename
        self.message = message
        self.line = line


class CSPValidator():
    """ Runs the validation rules """

    rules = [

        # Matches on src attributes with an http[s] protocol
        CSPRule(
            "<(img|script).*?\ssrc\s?=\s?[\"']+http[^\"\']*[\"\']?",
            "External resources are not allowed",
            "csp_chromeapps"
        ),

        # Matches on src attributes with an http[s] protocol
        CSPRule(
            "<link.+?href\s?=\s?[\"']+http[^\"\']*[\"\']?",
            "External resources are not allowed",
            "csp_chromeapps"
        ),

        # Matches on scripts with non-whitespace contents
        CSPRule(

            # Opening tag
            "(?ms)<script[^>]*>[^<]+?" +

            # Non-whitespace chars that are _not_ closing the tag
            "[^\s<]+?" +

            # Now non-greedy fill to the end of the tag
            ".*?</script>",

            "Inline scripts are not allowed"
        ),

        # Matches on eval / new Function
        CSPRule(
            "eval|new Function",
            "Code creation from strings, e.g. eval / new Function not allowed"
        ),

        # Matches on eval / new Function
        CSPRule(
            "setTimeout\s?\(\"[^\"]*\"",
            "Code creation from strings, e.g. setTimeout(\"string\") is not allowed"
        ),

        # Matches on on{event}
        CSPRule(
            "<.*?\son.*?=",
            "Event handlers should be added from an external src file"
        ),

        # Matches external resources in CSS
        CSPRule(
            "url\(\"?(?:https?:)?//[^\)]*\)",
            "External resources are not allowed",
            "csp_chromeapps"
        ),

        # Matches hrefs with a javascript: url
        CSPRule(
            "<.*?href.*?javascript:.*?>",
            "Inline JavaScript calls are not allowed",
            "csp_chromeapps"
        )
    ]

    def get_view_contents(self, view):
        return view.substr(sublime.Region(0, view.size()))

    def validate_contents(self, contents, filename):
        errors = []

        for rule in self.rules:
            for match in re.finditer( rule.rule, contents ) :
                # TODO: this is suboptimal, consider refactoring
                line = contents.count("\n", 0, match.start())+1
                errors.append(
                    CSPError(filename, line, rule.message)
                )

        return errors


class csp_validate_files(sublime_plugin.ApplicationCommand):
    """ Main Validator Class """
    validator = CSPValidator()

    def is_valid_file_type(self, filename):
        """ Checks that the file is worth checking """
        if filename == None:
            return False

        fn = filename.lower()
        return re.compile('(.html?|.js)$').search(fn)!=None

    def run_validator_all_files(self):
        projectRoot = ChromeApp.findProjectRoot(sublime.active_window().active_view().file_name())
        if (projectRoot):
            errors = self.run_validator_on_dir(projectRoot);
            self.show_errors(projectRoot, errors)
        else:
            sublime.message_dialog(
                "Could not detect a valid Chrome App manifest for this file:\n%s\n\n"
                "You need a file manifest.json in the same dir or in any parent dir of this file." % sublime.active_window().active_view().file_name())

    def run_validator_on_dir(self, dir):
        errors = []
        for f in os.listdir(dir):
            filename = os.path.join(dir, f)
            if os.path.isdir(filename):
                errors = errors + self.run_validator_on_dir(filename)
            else:
                errors = errors + self.run_validator(filename)
        return errors

    def run_validator(self, filename):
        # early return for anything not using the correct syntax
        if not self.is_valid_file_type(filename):
            return []

        contents = open(filename, "r").read()
        # Get the file and send to the validator
        return self.validator.validate_contents(contents, filename)

    def show_errors(self, projectRoot, errors):
        if len(errors) <= 0:
            sublime.message_dialog("Hooray! Apparently there are no CSP violations in project:\n%s" % projectRoot)
            return

        errorView = sublime.active_window().new_file()
        errorView.settings().set("projectRoot", projectRoot)
        errorView.set_scratch(True)
        errorView.set_name(CSP_VIOLATIONS_NAME)
        edit = errorView.begin_edit()

        text = ( "Project %s\n\n%d CSP violation%s found\n" % 
            (projectRoot, len(errors), "s" if len(errors)>1 else ""))

        text += "(double click on filenames to jump into violations)\n\n"

        for e in errors:
            text+="%s:%s\n" % (e.filename[len(projectRoot)+1:], e.line)
            text+="CSP rule: %s\n\n" % e.message

        errorView.insert(edit, 0, text)

        errorView.end_edit(edit)
        errorView.set_syntax_file("%s%s%s%s%s" % 
            (sublime.packages_path(), os.sep, ChromeApp.PACKAGE_NAME, os.sep, CSP_VIOLATIONS_SYNTAX))

    def csp_rule_clicked(self, index):
        if index<0:
            return
        filename=self.errors[index].filename
        line=self.errors[index].line
        sublime.active_window().open_file("%s:%d" % (filename, line), 
            sublime.ENCODED_POSITION)

    def run(self):
        self.run_validator_all_files()


class goto_file(sublime_plugin.TextCommand):

    def is_applicable(self):
        return (self.view.settings().get('syntax').find(CSP_VIOLATIONS_SYNTAX)>=0 
            and self.view.name()==CSP_VIOLATIONS_NAME
            and self.view.settings().has("projectRoot"))


    def run_(self, args):
        if self.is_applicable() and len(self.view.sel())==1:
            i = self.view.line(self.view.sel()[0])
            line = self.view.substr(i)
            m = re.compile(r"([^:]+):(\d+)").match(line)
            if m!=None:
                projectRoot = self.view.settings().get("projectRoot")
                filename = m.group(1)
                fileline = int(m.group(2))
                sublime.active_window().open_file("%s:%d" % 
                    (os.path.join(projectRoot, filename), 
                        fileline), sublime.ENCODED_POSITION)
            else:
                self.run_original_command(args)

        else:
            self.run_original_command(args)

    def run_original_command(self, args):
        myargs = args["bypass_if_not_applicable"]
        original_command = myargs["press_command"]
        if original_command:
          original_args = dict({"event": args["event"]}.items() + myargs["press_args"].items())
          self.view.run_command(original_command, original_args)
