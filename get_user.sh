#!/usr/bin/env bash
set -x
set -e

if [ -z "$GITHUB_ACCESS_TOKEN" ]
then
      echo "Error: Environment variable GITHUB_ACCESS_TOKEN is not set"
      exit 1
fi

curl -H "Authorization: token $GITHUB_ACCESS_TOKEN" -i https://api.github.com/user
