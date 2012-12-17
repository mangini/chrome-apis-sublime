import sublime
import sublime_plugin
import re
import os
import ChromeApp


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

    def __init__(self, filename, message):
        self.filename = filename
        self.message = message


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

    def validate_contents(self, contents):
        errors = []

        for rule in self.rules:
            matches = rule.rule.search(contents)
            if (matches): 
                for match in matches:
                    errors.append(
                        CSPError(match, rule.message)
                    )

        return errors


class csp_validate_old(sublime_plugin.WindowCommand):

    def xrun(self):
        self.violations = [
            {"file": "extensions.json", "line": 137, "message": "Cannot use inline scripts on HTML"},
            {"file": "index.js", "line": 11, "message": "Cannot use eval()"}]
        quick_panel = []
        for v in self.violations:
            quick_panel.append([
                "%s line %d" % (v['file'], v['line']),
                "CSP rule: %s" % v['message']])

        self.window.show_quick_panel(quick_panel, self.csp_rule_clicked)

    def csp_rule_clicked(self, index):
        if index<0:
            return
        filename=self.violations[index]['file']
        line=self.violations[index]['line']
        self.window.open_file("%s:%d" % (filename, line), 
            sublime.ENCODED_POSITION)


class csp_validate_files(sublime_plugin.ApplicationCommand):
    """ Main Validator Class """
    errors = []
    validator = CSPValidator()

    def is_valid_file_type(self, filename):
        """ Checks that the file is worth checking """
        return filename != None and filename.endswith(".js")

    def run_validator_all_files(self):
        projectRoot = ChromeApp.findProjectRoot(sublime.active_window().active_view().file_name())
        self.run_validator_on_dir(projectRoot);
        if len(self.errors) > 0:
            self.show_errors()

    def run_validator_on_dir(self, dir):
        for f in os.listdir(dir):
            filename = os.path.join(dir, f)
            if os.path.isdir(filename):
                self.run_validator_on_dir(filename)
            else:
                self.run_validator(filename)

    def run_validator(self, filename):
        # early return for anything not using the correct syntax
        if not self.is_valid_file_type(filename):
            return

        contents = open(filename, "r").read()
        # Get the file and send to the validator
        self.errors.append(self.validator.validate_contents(contents))

    def show_errors(self):
#        self.violations = [
#            {"file": "extensions.json", "line": 137, "message": "Cannot use inline scripts on HTML"},
#            {"file": "index.js", "line": 11, "message": "Cannot use eval()"}]
        quick_panel = []
        for v in self.errors:
            quick_panel.append([
                "%s" % v.message,
                "%s" % v.message])
#                "%s line %d" % (v['file'], v['line']),
#                "CSP rule: %s" % v['message']])

        self.window.show_quick_panel(quick_panel, self.csp_rule_clicked)

    def csp_rule_clicked(self, index):
        if index<0:
            return
        filename=self.errors[index].message
#        line=self.violations[index]['line']
#        self.window.open_file("%s:%d" % (filename, line), 
#            sublime.ENCODED_POSITION)

    def run(self):
        self.run_validator_all_files()
