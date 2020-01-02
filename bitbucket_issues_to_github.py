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


def query_gissues():
    # The issues endpoint is a paginated API.
    # We need to iterate over all issues to make this script re-entrant.
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


def patch_gissue(gissue, bissue):
    if gissue['title'] != bissue['title']:
        raise ValueError('Inconsistent issues')

    glabels = set()
    bassignee = bissue['assignee']
    if bassignee is None:
        gassignees = []
    elif bassignee in USER_MAPPING:
        gassignees = [USER_MAPPING[bassignee]]
    else:
        gassignees = []

    bstatus = bissue['status']
    if bstatus == 'new' or bstatus == 'open':
        gstate = 'open'
    else:
        gstate = 'closed'

    bkind = bissue['kind']
    if bkind in KIND_MAPPING:
        glabels.add(KIND_MAPPING[bkind])
    else:
        glabels.add(bkind)

    if bstatus in STATUS_MAPPING:
        glabels.add(STATUS_MAPPING[bstatus])

    gissue_patch = {
        "assignees": gassignees,
        "labels": list(glabels),
        "state": gstate,
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


def bitbucket_to_github(bitbucket):
    bissues = bitbucket['issues']
    old_gissues = query_gissues()
    print('Number of github issues in ' + repo_url() + ' before POSTing:', len(old_gissues))
    print('Number of bitbucket issues in ' + f_name + ':', len(bissues))
    if len(bissues) == 0:
        raise ValueError('Could not find any issue in ' + f_name)
    for bissue in bissues:
        gissue = find_gissue_with_bissue_title(gissues=old_gissues, bissue=bissue)
        if gissue is None:
            gissue = post_bissue_to_github(bissue=bissue)
        patch_gissue(gissue=gissue, bissue=bissue)


def main():
    global f_name
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <bitbucket export json file>')
        exit(-1)
    f_name = sys.argv[1]

    if 'GITHUB_ACCESS_TOKEN' not in os.environ:
        raise ValueError('Environment variable GITHUB_ACCESS_TOKEN is not set')

    with open(f_name, 'r') as f:
        bitbucket_to_github(bitbucket=read_json_file(f))


main()
