import random

AVATAR_CHOICES = [
    "terminal-hacker",
    "robot",
    "bug-monster",
    "code-cat",
    "cpu-brain",
    "wifi-wizard",
    "binary-ghost",
    "docker-whale",
    "git-octopus",
    "code-ninja",
    "keyboard-warrior",
    "stack-overflow",
    "404-alien",
    "firewall-guard",
    "one-up-mushroom",
    "recursion-owl",
    "rubber-duck",
    "infinite-coffee",
    "sudo-penguin",
    "null-pointer",
]


def random_avatar():
    return random.choice(AVATAR_CHOICES)
