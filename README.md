# Bitbucket To Github Issues Migration

<a href="https://github.com/fkirc/bitbucket-issues-to-github/actions?query=branch%3Amaster"><img alt="CI status" src="https://github.com/fkirc/bitbucket-issues-to-github/workflows/Tests/badge.svg/?branch=master"></a>

A simple Python script to migrate both Bitbucket issues and comments to a Github repo.

## Why should I use this instead of other scripts?

Compared to other scripts, this script has two key properties:
It is both idempotent and simple.

The simplicity enables you to easily customize this script for your needs.
The idempotency enables you to tweak this script even after running the initial migration, such that you can tweak the migrated issues without duplicating the issues.

## How to use it

Firstly, export the issues from your Bitbucket repo via the Bitbucket web interface.
This Bitbucket export yields two JSON files:
`db-1.0.json` and `db-2.0.json`.
This script only works with the `db-1.0.json` file.
The Bitbucket export can be only done by Bitbucket repo administrators.

Secondly, obtain a "Personal Access Token" for the Github API.
Set your token as an environment variable:  
`export GITHUB_ACCESS_TOKEN=<your access token>`

Thirdly, configure this script in [config.py](config.py).
The only mandatory configuration is `TARGET_REPO`, which needs to be configured to `<repo owner>/<repo name>`.
All other configurations can be kept as is.

Once you have met these prerequisites and setup the dependencies, you can run the migration:

`python3 bitbucket_issues_to_github.py db-1.0.json`


## Dependencies

Python3 is required.
A simple way to setup the dependencies is to use Python3's `venv` tool:

`python3 -m venv py3`  
`source ./py3/bin/activate`  
`pip3 install -r requirements.txt`

## Why can't I use my Github password?

Github deprecated password authentication for several API endpoints.
Instead, Github recommends to use "Personal Access Tokens" to access their API.
Moreover, your Github password does not work if you are using Github two factor authentication.
Therefore, this script does not support authentication via your regular Github password.

## Additional features

I do not actively add new features to this script.
However, if you have very specific migration-needs, then we could setup a one-off-contract to migrate issues within your organization.

## Sidenotes

Although not required, I recommend to migrate to a fresh Github repo with zero issues. By doing so, the old Bitbucket issue numbers should remain valid after the migration.
