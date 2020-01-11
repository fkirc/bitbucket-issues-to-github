#!/bin/bash
set -e
set -x

python3 bitbucket_issues_to_github.py 'tests/testdata/db-1.0.json'

