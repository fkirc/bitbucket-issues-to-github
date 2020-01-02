#!/usr/bin/python
import json
import sys
import os
import requests
from requests import Request
from requests_toolbelt.utils import dump
import requests_toolbelt

TARGET_REPO = 'ThomasOlip/random-gallery'

# Github only accepts assignees from valid users. We need to map those users from bitbucket.
USER_MAPPING = {
    'martin_gaertner': 'MartinGaertner',
    'thomas_o': 'ThomasOlip',
    'fkirc': 'fkirc'
}

f_name=None

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

def query_gissues():
    # The issues endpoint is a paginated API.
    # We need to iterate over all issues to make this script re-entrant.
    query_url = issue_url()
    issues = []
    while True:
        res = do_request(Request('GET', url=query_url, params={'per_page': 100}, headers=github_headers()))
        issues.extend(res.json())
        if 'next' in res.links:
            query_url  = res.links['next']['url']
        else:
            break
    return issues

def post_bissue_to_github(bissue):
    # We patch the remaining elements right after posting the issue.
    incomplete_gissue = {
      "title": bissue['title'],
      "body": bissue['content'],
    }
    res = do_request(Request('POST', url=issue_url(), headers=github_headers(), json=incomplete_gissue))
    full_gissue = res.json()
    return full_gissue

def is_gissue_patch_different(gissue, gissue_patch):
    if gissue['state'] != gissue_patch['state']:
        return True
    gissue_assignees = gissue['assignees']
    gissue_labels = gissue['labels']
    gissue_patch_assignees = gissue_patch['assignees']
    gissue_patch_labels = gissue_patch['labels']
    if len(gissue_assignees) != len(gissue_patch_assignees):
        return True
    if len(gissue_labels) != len(gissue_patch_labels):
        return True
    if len(gissue_assignees) > 0 and gissue_assignees[0]['login'] != gissue_patch_assignees[0]:
        return True
    if len(gissue_labels) > 0 and gissue_labels[0]['name'] != gissue_patch_labels[0]:
        return True
    return False

def patch_gissue(gissue, bissue):
    if gissue['title'] != bissue['title']:
        raise ValueError('Inconsistent issues')

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

    gissue_patch = {
        "assignees": gassignees,
        "labels": [bissue['kind']],
        "state": gstate,
    }
    if is_gissue_patch_different(gissue=gissue, gissue_patch=gissue_patch):
        do_request(Request('PATCH', url=issue_url() + '/' + str(gissue['number']), headers=github_headers(), json=gissue_patch))
    else:
        print('Skip issue "' + gissue['title'] + '" since there are no changes compared to ' + repo_url())

def find_gissue_with_bissue_title(gissues, bissue):
    for gissue in gissues:
        if gissue['title'] == bissue['title']:
            return gissue
    return False

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
        #break

def main():
    global f_name
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <bitbucket export json file>')
        exit(-1)
    f_name = sys.argv[1]

    if 'GITHUB_ACCESS_TOKEN' not in os.environ:
        raise ValueError('Environment variable GITHUB_ACCESS_TOKEN is not set')
        exit(-1)

    with open(f_name, 'r') as f:
        bitbucket_to_github(bitbucket=read_json_file(f))

main()
