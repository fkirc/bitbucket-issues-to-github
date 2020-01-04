
TARGET_REPO = 'ThomasOlip/random-gallery'

# Github only accepts assignees from valid users. We map those users from bitbucket.
USER_MAPPING = {
    'martin_gaertner': 'MartinGaertner',
    'thomas_o': 'ThomasOlip',
    'fkirc': 'fkirc',
}

# We map bitbucket's issue "kind" to github "labels".
KIND_MAPPING = {
    "task": "enhancement",
    "proposal": "suggestion",
}

# The only github statuses are "open" and "closed".
# Therefore, we map some bitbucket statuses to github "labels".
STATUS_MAPPING = {
    "on hold": "suggestion",
}

# Bitbucket has several issue states.
# All states that are not listed in this set will be closed.
OPEN_ISSUE_STATES = {
    "open",
    "new",
    "on hold",
}
