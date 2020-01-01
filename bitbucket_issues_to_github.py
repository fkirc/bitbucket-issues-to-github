#!/usr/bin/python
import json
import sys
import os
import requests
import logging

TARGET_REPO='ThomasOlip/random-gallery'

def repo_url():
    return 'https://api.github.com/repos/' + TARGET_REPO

def issue_url():
    return repo_url() + '/issues'

def read_json_file(f):
    json_object = json.loads(f.read())
    print(json_object)
    return json_object

def github_headers():
    return {'Authorization': 'token ' + os.environ['GITHUB_ACCESS_TOKEN']}

def create_github_issues(issues):
    print('Number of exported bitbucket issues:', len(issues))

def query_github_issues():
    r = requests.get(url = issue_url(), headers = github_headers())
    if not r.ok:
        r.raise_for_status()
    issues = r.json()
    print(issues)
    return issues

def bitbucket_to_github(bitbucket):
    gissues = query_github_issues()
    print('Number of github issues before import:', len(gissues))
    create_github_issues(bitbucket['issues'])

def main():
    logging.basicConfig(level=logging.DEBUG)
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
