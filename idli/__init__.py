#!/usr/bin/python

_status_mapping = {"open" : True,
                   "closed" : False,
                   "true" : True,
                   "false" : False
                   }

def set_status_mapping(d):
    global _status_mapping
    _status_mapping = {}
    for k in list(d.keys()):
        _status_mapping[k.lower()] = d[k]

def get_status_mapping():
    global _status_mapping
    return _status_mapping

class User(object):
    def __init__(self, id, mail, shortname=None, longname=None):

        self.id = str(id)
        self.mail = str(mail)

        if shortname is not None:
            self.shortname = str(shortname)
        else:
            self.shortname = str(self.id)

        if longname is not None:
            self.longname = str(longname)
        else:
            self.longname = str(self.shortname)

    def __str__(self):
        return "User(" + self.id + ", " + self.mail + ", " + self.shortname + ", " + self.longname + ")"

class Issue(object):
    def __init__(self, title, body, id, creator, status = True, num_comments = None, create_time=None, last_modified=None, owner=None, tags=[]):
        self.title = title
        self.body = body
        self.id = str(id)
        self.creator = creator
        self.num_comments = int(num_comments or 0)
        self.status = self.__parse_status(status)
        self.create_time = create_time
        self.last_modified = last_modified
        self.owner = owner
        self.tags = tags

    def __parse_status(self, status):
        if (status.__class__ == bool):
            return status
        if (status.__class__ == str or status.__class__ == str):
            return get_status_mapping()[status.lower()]

    def __str__(self):
        return "Issue(" + self.id + ", " + self.title + ", " + self.creator + ", " + str(self.status) + ")"

class IssueComment(object):
    def __init__(self, issue, creator, title, body, date=None, tags=[]):
        self.issue = issue
        self.creator = creator
        self.title = title
        self.body = body
        self.date = date
        self.tags = tags

class Backend(object):
    def __init__(self):
        raise IdliException("__init__ is not implemented by this backend.")

    def initialize(self):
        section_name = self.config_section or self.name
        print("Initializing " + self.name + " project.")
        import idli.config as cfg

        if(self.args.no_verify):
            cfg.set_config_value(section_name, 'verify_ssl', "False", global_val=False)

        for (name, help) in self.init_names:
            cfg.set_config_value(section_name, name, self.args.__dict__[name], global_val=False)

        cfg.set_config_value("project", "type", self.name, global_val=False)
        print("Wrote configuration to " + cfg.local_config_filename())

    def configure(self):
        section_name = self.config_section or self.name
        print("Configuring backend  " + self.name)
        import idli.config as cfg
        for (name,help) in self.config_names:
            cfg.set_config_value(section_name, name, self.args.__dict__[name], global_val=not self.args.local_only)
        cfg.set_config_value("project", "type", self.name, global_val=not self.args.local_only)
        if (not self.args.local_only):
            print("Wrote configuration to " + cfg.global_config_filename())
        else:
            print("Added local configuration to " + cfg.global_config_filename())

    def add_issue(self, title, body, tags=[]):
        raise IdliNotImplementedException("add_issue is not implemented by this backend.")

    def tag_issue(self, issue_id, add_tags, remove_tags=[]):
        raise IdliNotImplementedException("tag_issue is not implemented by this backend.")

    def issue_list(self, state=True):
        raise IdliNotImplementedException("issue_list is not implemented by this backend.")

    def filtered_issue_list(self, state=True, mine=False, tag=None):
        issues = self.issue_list(state)
        if mine:
            issues = [i for i in issues if i.owner == self.username()]
        if tag:
            issues = [i for i in issues if tag in i.tags]
        return issues

    def get_issue(self, issue_id):
        raise IdliNotImplementedException("get_issue is not implemented by this backend.")

    def resolve_issue(self, issue_id, status = "closed", message = None):
        raise IdliNotImplementedException("resolve_issue resolve_issue is not implemented by this backend.")

    def add_comment(self, issue_id, body):
        raise IdliNotImplementedException("add_comment is not implemented by this backend.")

    def assign_issue(self, issue_id, user, message):
        raise IdliNotImplementedException("assign_issue is not implemented by this backend.")

    def username(self):
        raise IdliNotImplementedException("username is not implemented by this backend.")

    def verify_ssl(self):
        try:
            if self._verify_ssl is not None:
                return self._verify_ssl
        except AttributeError:
            self._verify_ssl = True

        try:
            cfg_verifssl = self.get_config("verify_ssl")

            if(cfg_verifssl == "False"):
                self._verify_ssl = False
            else:
                self._verify_ssl = True
        except:
            self._verify_ssl=True
        
        return self._verify_ssl


    #Utilities
    def get_config(self, name):
        import idli.config as cfg
        return cfg.get_config_value(self.config_section, name)

class IdliException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class IdliNotImplementedException(IdliException):
    pass

# vim: set sw=4 ts=4 expandtab:
