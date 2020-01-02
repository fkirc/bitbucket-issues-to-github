#!/usr/bin/python
import json
import sys
import os
import requests
from requests import Request
from requests_toolbelt.utils import dump
import requests_toolbelt

TARGET_REPO = 'ThomasOlip/random-gallery'

# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
    'martin_gaertner': 'MartinGaertner',
    'thomas_o': 'ThomasOlip',
    'fkirc': 'fkirc',
}

# We map bitbucket's issue "kind" to github's issue "labels".
KIND_MAPPING = {
    "task": "enhancement",
    "proposal": "suggestion",
}

# The only github statuses are "open" and "closed".
# Therefore, we map some bitbucket issue statuses to github's issue "labels".
STATUS_MAPPING = {
    "on hold": "suggestion",
}

f_name = None


def repo_url():
    return 'https://api.github.com/repos/' + TARGET_REPO


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
    if bstatus == 'new' or bstatus == 'open':
        return 'open'
    else:
        return 'closed'


def map_bassignee_to_gassignees(bissue):
    bassignee = bissue['assignee']
    if bassignee is None:
        return []
    elif bassignee in USER_MAPPING:
        return [USER_MAPPING[bassignee]]
    else:
        return []


def map_bstatus_to_glabels(bissue, glabels):
    bstatus = bissue['status']
    if bstatus in STATUS_MAPPING:
        glabels.add(STATUS_MAPPING[bstatus])


def map_bkind_to_glabels(bissue, glabels):
    bkind = bissue['kind']
    if bkind in KIND_MAPPING:
        label = KIND_MAPPING[bkind]
    else:
        label = bkind
    glabels.add(label)


def patch_gissue(gissue, bissue):
    if gissue['title'] != bissue['title']:
        raise ValueError('Inconsistent issues')

    glabels = set()
    map_bkind_to_glabels(bissue=bissue, glabels=glabels)
    map_bstatus_to_glabels(bissue=bissue, glabels=glabels)

    gissue_patch = {
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
    print('Number of bitbucket issues in ' + f_name + ':', len(bissues))

    for bissue in bissues:
        gissue = find_gissue_with_bissue_title(gissues=old_gissues, bissue=bissue)
        if gissue is None:
            gissue = post_bissue_to_github(bissue=bissue)
        patch_gissue(gissue=gissue, bissue=bissue)


class BitbucketExport:
    def __init__(self, bissues, comment_map):
        self.bissues = bissues
        self.comment_map = comment_map


def parse_bitbucket_export(f):
    bexport_json = read_json_file(f)
    bissues = bexport_json['issues']
    if len(bissues) == 0:
        raise ValueError('Could not find any issue in ' + f_name)
    comments = bexport_json['comments']
    comment_map = {}
    for comment in comments:
        bidx = comment['issue']
        if bidx not in comment_map:
            comment_map[bidx] = []
        comment_map[bidx].append(comment)
    for comments in comment_map.values():
        comments.reverse()
    return BitbucketExport(bissues=bissues, comment_map=comment_map)


def main():
    global f_name
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <bitbucket export json file>')
        exit(-1)
    f_name = sys.argv[1]

    if 'GITHUB_ACCESS_TOKEN' not in os.environ:
        raise ValueError('Environment variable GITHUB_ACCESS_TOKEN is not set')

    with open(f_name, 'r') as f:
        bexport = parse_bitbucket_export(f=f)
        bitbucket_to_github(bexport=bexport)


main()
