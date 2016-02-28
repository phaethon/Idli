import datetime
import json
import logging
import urllib.request, urllib.parse, urllib.error

import requests

import idli
import idli.config as cfg

bitbucket_base_api_url = "https://api.bitbucket.org/{version}"
dateformat = "%Y-%m-%d %H:%M:%S"
bitbucket_status_mapping = {
    'new': True,
    'open': True,
    'resolved': False,
    'on hold': False,
    'invalid': False,
    'duplicate': False,
    'wontfix': False,
    'closed': False,
}
bitbucket_status_reverse_mapping = {
    True: ['new', 'open'],
    'open': ['new', 'open'],
    False: ['resovled', 'on hold', 'invalid', 'duplicate', 'wontfix', 'closed'],
    'closed': ['resovled', 'on hold', 'invalid', 'duplicate', 'wontfix', 'closed']
}

idli_has_logging = not not logging.getLogger('idli').handlers
logger = logging.getLogger('idli.backends.bitbucket')
if not idli_has_logging:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(levelname)s %(name)s] %(message)s'))
    handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.warn('No global logging detected, using local settings')

class HttpRequestException(Exception):
    def __init__(self, value, status_code):
        super(HttpRequestException, self).__init__(value)
        self.value = value
        self.status_code = status_code

    def __str__(self):
        return "HttpError: " + str(self.status_code) + ", " + str(self.value)

def catch_url_error(func):
    def wrapped_func(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HttpRequestException as e:
            raise idli.IdliException("Could not connect to Bitbucket. Error: " + str(e))
    return wrapped_func

def catch_HTTPError(func):
    def wrapped_func(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except HttpRequestException as e:
            if (e.status_code == 401):
                raise idli.IdliException("Authentication failed.\n\nCheck your idli configuration. The most likely cause is incorrect values for 'user' or 'password' variables in the [Bitbucket] section of the configuration files:\n    " + cfg.local_config_filename() + "\n    " + cfg.global_config_filename() + ".\n\nMake sure you check both files - the values in " + cfg.local_config_filename() + " will override the values in " + cfg.global_config_filename() + "." + "\n\n" + str(e))
            if (e.status_code == 404):
                self.validate()
            raise e
    return wrapped_func

def catch_missing_config(func):
    def wrapped_func(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except cfg.IdliMissingConfigException as e:
            raise idli.IdliException("You must configure idli for Bitbucket first. Run 'idli configure Bitbucket' for options.")
    return wrapped_func

class BitbucketBackend(idli.Backend):
    name = "bitbucket"
    config_section = "Bitbucket"
    init_names = [ ("repo", "Name of repository"),
                   ("owner", "Owner of repository (Bitbucket username).")
                   ]
    config_names = [ ("user", "Bitbucket username"),
                     ("password", "Bitbucket password"),
                     ]

    def __init__(self, args, repo=None, auth=None):
        logger.debug("__init__ args:%s repo:%s", args, repo)
        self.args = args
        if (repo is None):
            self.__repo_owner, self.__repo = None, None
        else:
            self.repo_owner, self.repo_name = repo
        if (auth is None):
            self.__user, self.__password = None, None
        else:
            self.__user, self.__password = auth
        idli.set_status_mapping(bitbucket_status_mapping)

    def repo(self):
        return self.__repo or self.get_config("repo")

    def repo_owner(self):
        return self.__repo_owner or self.get_config("owner")

    def username(self):
        return self.__user or self.get_config("user")

    def password(self):
        return self.__password or self.get_config("password")

    def auth(self):
        if self.username() and self.password():
            return (self.username(), self.password())
        return None
    
    def url(self, endpoint='repositories/{account_name}/{repo_slug}/issues', component=None, version='1.0', **kwargs):
        url_elements = [bitbucket_base_api_url, endpoint]
        if component:
            url_elements.append(component)
        url = '/'.join(url_elements)
        vals = {'version': version, 'account_name': self.repo_owner(), 'repo_slug': self.repo()}
        vals.update(kwargs)
        return url.format(**vals)

    @catch_missing_config
    @catch_url_error
    @catch_HTTPError
    def add_issue(self, title, body, tags=[]):
        logging.debug('add_issue, title: %s', title)
        url = self.url()
        result = self.__url_request('post', url, {'title': title, 'content': body})
        issue = self.__parse_issue(result)
        if tags:
            raise idli.IdliNotImplementedException('Tagging not supported')
        return (issue, [])

    @catch_missing_config
    @catch_url_error
    @catch_HTTPError
    def tag_issue(self, issue_id, tags, remove_tags=False):
        logging.debug('tag_issue')
        raise idli.IdliNotImplementedException('Tagging not supported')
        for t in tags:
            url = self.__add_label_url(issue_id, t, remove_tags)
            result = self.__url_request(url)
            if (not (t in result['labels'])) and (not remove_tags):
                raise idli.IdliException("Failed to add tag to issue " + str(issue_id) + ". The issue list may be in an inconsistent state.")
        return self.get_issue(issue_id)

    @catch_url_error
    @catch_HTTPError
    def issue_list(self, state=True):
        logging.debug('issue_list, state: %s', state)
        url = self.url()
        result = self.__url_request('get', url, {'status': bitbucket_status_reverse_mapping[state]})
        issues = []
        for i in result['issues']:
            issues.append(self.__parse_issue(i))
        return issues 

    @catch_url_error
    def get_issue(self, issue_id, get_comments=True):
        logging.debug('get_issue, issue_id: %s', issue_id)
        issue_url = self.url(component='{issue_id}', issue_id=issue_id)
        comment_url = self.url(component='{issue_id}/comments', issue_id=issue_id)
        try:
            issue_as_json = self.__url_request('get', issue_url)
            comments_as_json = self.__url_request('get', comment_url)
        except urllib2.HTTPError as e:
            self.validate()
            raise idli.IdliException("Could not find issue with id '" + issue_id + "'")

        issue = self.__parse_issue(issue_as_json)
        comments = []
        for c in comments_as_json:
            comments.append(self.__parse_comment(issue, c))
        return (issue, comments)

    @catch_missing_config
    @catch_HTTPError
    @catch_url_error
    def add_comment(self, issue_id, body):
        logging.debug('add_comment, issue_id: %s', issue_id)
        url = self.url(component='{issue_id}/comments', issue_id=issue_id)
        result = self.__url_request('post', url, {'content': body})
        comment = self.__parse_comment(None, result)
        return comment

    @catch_missing_config
    @catch_url_error
    @catch_HTTPError
    def resolve_issue(self, issue_id, status = "closed", message = None):
        logging.debug('resolve_issue, issue_id: %s, status: %s', issue_id, status)
        if message:
            self.add_comment(issue_id, message)
        url = self.url(component='{issue_id}', issue_id=issue_id)
        response = self.__url_request('put', url, {"status": status})
        issue = self.__parse_issue(response)
        return issue

    #Validation queries
    def validate(self):
        self.__validate_user()
        self.__validate_repo()

    @catch_url_error
    def __validate_user(self):
        test_url = self.url(endpoint='users', component='{account_name}')
        try:
            result = json.loads(urllib.request.urlopen(test_url).read())
            return result['user']
        except urllib.error.HTTPError as e:
            raise idli.IdliException("Can not find user " + self.repo_owner() + " on github.")

    @catch_url_error
    def __validate_repo(self):
        test_url = self.url(endpoint='repositories', component='{account_name}/{repo_slug}')
        try:
            result = json.loads(urllib.request.urlopen(test_url).read())
            return result['repository']
        except urllib.error.HTTPError as e:
            raise idli.IdliException("Can not find repository " + self.repo() + " on github.")

    #Utilities
    def __url_request(self, method, url, data=None):
        logger.debug('__url_request, method: %s, url: %s, data: %s', method, url, data)
        if method.lower() == 'get':
            response = requests.get(url, auth=self.auth(), params=data)
        else:
            response = requests.request(method, url, auth=self.auth(), data=data)
        logger.debug('__url_request, status_code: %s, response: %s', response.status_code, response.content)
        if (response.status_code - (response.status_code % 100)) != 200: #200 responses are all legitimate
            raise HttpRequestException("HTTP error", response.status_code)
        return response.json()

    def __parse_comment(self, issue, cdict):
        return idli.IssueComment(issue, cdict["author_info"]["username"], "", cdict["content"], self.__parse_date(cdict["utc_created_on"]))

    def __parse_issue(self, issue_dict):
        #TODO: timezones
        create_time = self.__parse_date(issue_dict["utc_created_on"])
        comment_count = issue_dict.get("comment_count", 0)
        #TODO: pseudotags for fields
        return idli.Issue(issue_dict["title"], issue_dict["content"],
                            issue_dict["local_id"], issue_dict["reported_by"]["username"],
                            num_comments = comment_count, status = issue_dict["status"],
                            create_time=create_time, tags=[])

    def __parse_date(self, datestr):
        return datetime.datetime.strptime(datestr[0:19], dateformat)


