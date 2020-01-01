#!/usr/bin/python
import json
import sys
import os
import requests
from requests import Request
from requests_toolbelt.utils import dump
import requests_toolbelt

TARGET_REPO='ThomasOlip/random-gallery'

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
    print(json_object)
    return json_object

def github_headers():
    return {'Authorization': 'token ' + os.environ['GITHUB_ACCESS_TOKEN'],
            'User-Agent': requests_toolbelt.user_agent('bitbucket_issues_to_github', '1.0.0')
            }

def query_github_issues():
    res = do_request(Request('GET', url = issue_url(), headers = github_headers()))
    return res.json()

def bissue_to_gissue(bissue):
    return {
      "title": bissue['title'],
      "body": bissue['content'],
      "assignees": [
        bissue['assignee']
      ],
      "milestone": 1,
      "labels": []
    }

def bitbucket_to_github(bitbucket):
    bissues = bitbucket['issues']
    old_gissues = query_github_issues()
    print('Number of github issues before import:', len(old_gissues))
    print('Number of exported bitbucket issues:', len(bissues))
    bissue = bissues[0]
    gissue = bissue_to_gissue(bissue=bissue)

def main():
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <bitbucket export json file>')
        exit(-1)
    f_name = sys.argv[1]

    if 'GITHUB_ACCESS_TOKEN' not in os.environ:
        print('Error: Environment variable GITHUB_ACCESS_TOKEN is not set')
        exit(-1)

    with open(f_name, 'r') as f:
        bitbucket_to_github(bitbucket=read_json_file(f))

main()
