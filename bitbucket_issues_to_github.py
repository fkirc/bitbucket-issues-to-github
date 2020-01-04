#!/usr/bin/python
import json
import sys
import os
from dateutil import parser
import requests
from requests import Request
from requests_toolbelt.utils import dump
import requests_toolbelt
import config


def repo_url():
    return 'https://api.github.com/repos/' + config.TARGET_REPO


def issue_url():
    return repo_url() + '/issues'


def do_request(req):
    prep_req = req.prepare()
    s = requests.session()
    res = s.send(prep_req)
    data = dump.dump_all(res)
    print(data.decode('utf-8'))
    if not res.ok:
        res.raise_for_status()
    return res


def read_json_file(f):
    json_object = json.loads(f.read())
    return json_object


def github_headers():
    return {'Authorization': 'token ' + os.environ['GITHUB_ACCESS_TOKEN'],
            'User-Agent': requests_toolbelt.user_agent('bitbucket_issues_to_github', '1.0.0')
            }


def do_github_request(req):
    req.headers.update(github_headers())
    return do_request(req)


def query_all_repo_gissues():
    # The issues endpoint is a paginated API.
    # We need to iterate over all issues to make this script idempotent.
    query_url = issue_url()
    issues = []
    while True:
        res = do_github_request(Request('GET', url=query_url, params={'per_page': 100, 'state': 'all'}))
        issues.extend(res.json())
        if 'next' in res.links:
            query_url = res.links['next']['url']
        else:
            break
    return issues


def post_bissue_to_github(bissue):
    # We patch the remaining elements right after posting the issue.
    incomplete_gissue = {
        "title": bissue['title'],
        "body": bissue['content'],
    }
    res = do_github_request(Request('POST', url=issue_url(), json=incomplete_gissue))
    full_gissue = res.json()
    return full_gissue


def is_gissue_patch_different(gissue, gissue_patch):
    if gissue['state'] != gissue_patch['state']:
        return True
    if gissue['body'] != gissue_patch['body']:
        return True

    patch_assignees = set(gissue_patch['assignees'])
    current_assignees = set(map(lambda assignee: assignee['login'], gissue['assignees']))
    if current_assignees != patch_assignees:
        return True

    patch_labels = set(gissue_patch['labels'])
    current_labels = set(map(lambda label: label['name'], gissue['labels']))
    if current_labels != patch_labels:
        return True
    return False


def map_bstatus_to_gstate(bissue):
    bstatus = bissue['status']
    if bstatus in config.OPEN_ISSUE_STATES:
        return 'open'
    else:
        return 'closed'


def map_bassignee_to_gassignees(bissue):
    bassignee = bissue['assignee']
    if bassignee is None:
        return []
    elif bassignee in config.USER_MAPPING:
        return [config.USER_MAPPING[bassignee]]
    else:
        return []


def map_bstatus_to_glabels(bissue, glabels):
    bstatus = bissue['status']
    if bstatus in config.STATUS_MAPPING:
        glabels.add(config.STATUS_MAPPING[bstatus])


def map_bkind_to_glabels(bissue, glabels):
    bkind = bissue['kind']
    if bkind in config.KIND_MAPPING:
        label = config.KIND_MAPPING[bkind]
    else:
        label = bkind
    glabels.add(label)


def time_string_to_date_string(timestring):
    datetime = parser.parse(timestring)
    return datetime.strftime("%Y-%m-%d")


def append_time_label(sb, timestring, label):
    sb.append('\n[' + label + ': ' + timestring + ']')


def append_bcomment(sb, bcomment):
    content = bcomment['content']
    if content is None:
        return  # There are bitbucket comments without any content. We ignore them.
    sb.append('\n')
    comment_label = 'Comment created by ' + bcomment['user']
    comment_created_on = time_string_to_date_string(timestring=bcomment['created_on'])
    append_time_label(sb=sb, timestring=comment_created_on, label=comment_label)
    sb.append('\n')
    sb.append(content)


def construct_gissue_content(bissue, bexport):
    sb = [bissue['content'], '\n']
    created_on = time_string_to_date_string(timestring=bissue['created_on'])
    updated_on = time_string_to_date_string(timestring=bissue['updated_on'])
    append_time_label(sb=sb, timestring=created_on, label='Issue created by ' + bissue['reporter'])
    if created_on != updated_on:
        append_time_label(sb=sb, timestring=updated_on, label='Last updated on bitbucket')
    bcomments = bexport.comment_map[bissue['id']]
    for bcomment in bcomments:
        append_bcomment(sb=sb, bcomment=bcomment)
    return ''.join(sb)


def patch_gissue(gissue, bissue, bexport):
    if gissue['title'] != bissue['title']:
        raise ValueError('Inconsistent issues')

    glabels = set()
    map_bkind_to_glabels(bissue=bissue, glabels=glabels)
    map_bstatus_to_glabels(bissue=bissue, glabels=glabels)

    gissue_patch = {
        "body": construct_gissue_content(bissue=bissue, bexport=bexport),
        "assignees": map_bassignee_to_gassignees(bissue=bissue),
        "labels": list(glabels),
        "state": map_bstatus_to_gstate(bissue=bissue),
    }
    if is_gissue_patch_different(gissue=gissue, gissue_patch=gissue_patch):
        do_github_request(Request('PATCH', url=issue_url() + '/' + str(gissue['number']), json=gissue_patch))
    else:
        print('Skip issue "' + gissue['title'] + '" since there are no changes compared to ' + repo_url())


def find_gissue_with_bissue_title(gissues, bissue):
    for gissue in gissues:
        if gissue['title'] == bissue['title']:
            return gissue
    return None


def bitbucket_to_github(bexport):
    bissues = bexport.bissues
    old_gissues = query_all_repo_gissues()

    print('Number of github issues in ' + repo_url() + ' before POSTing:', len(old_gissues))
    print('Number of bitbucket issues in ' + bexport.f_name + ':', len(bissues))

    for bissue in bissues:
        gissue = find_gissue_with_bissue_title(gissues=old_gissues, bissue=bissue)
        if gissue is None:
            gissue = post_bissue_to_github(bissue=bissue)
        patch_gissue(gissue=gissue, bissue=bissue, bexport=bexport)


class BitbucketExport:
    def __init__(self, bissues, comment_map, f_name):
        self.bissues = bissues
        self.comment_map = comment_map
        self.f_name = f_name


def parse_bitbucket_export(f, f_name):
    print('Parsing ' + f_name + '...')
    bexport_json = read_json_file(f)
    bissues = bexport_json['issues']
    if len(bissues) == 0:
        raise ValueError('Could not find any issue in ' + f_name)
    comments = bexport_json['comments']
    comment_map = {}
    for bissue in bissues:
        comment_map[bissue['id']] = []
    for comment in comments:
        bissue_idx = comment['issue']
        comment_map[bissue_idx].append(comment)
    for comments in comment_map.values():
        comments.reverse()
    return BitbucketExport(bissues=bissues, comment_map=comment_map, f_name=f_name)


def main():
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <bitbucket export json file>')
        exit(-1)
    f_name = sys.argv[1]

    if 'GITHUB_ACCESS_TOKEN' not in os.environ:
        raise ValueError('Environment variable GITHUB_ACCESS_TOKEN is not set')

    with open(f_name, 'r') as f:
        bexport = parse_bitbucket_export(f=f, f_name=f_name)
        bitbucket_to_github(bexport=bexport)


main()
