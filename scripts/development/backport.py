#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import yaml
from git import Repo
from gitdb.exc import BadName
from github import Github


def get_pr_num_from_message(message):
    title = message.split("\n")[0]
    if "(#" not in title:
        return None

    return int(title.split("(#")[-1].strip(")"))


def get_commit_and_pr(repo, commit_or_pr):
    # Make sure we have the latest version of the main branch to search for the
    # commit
    repo.heads["main"].checkout()
    repo.remotes["origin"].pull()

    try:
        # If argument is an integer treat it as PR number, else commit ID
        pr = int(commit_or_pr)
    except ValueError:
        try:
            commit = repo.commit(commit_or_pr)
            pr = get_pr_num_from_message(commit.message)
        except BadName:
            # Lookup commit ID
            print(f"Can't find commit {commit_or_pr}")
            sys.exit(1)
    else:
        for commit in repo.iter_commits("main"):
            if get_pr_num_from_message(commit.message) == pr:
                break
        else:
            print(f"Can't find PR {pr}")
            sys.exit(1)

    return commit, pr


def parse_args():
    parser = argparse.ArgumentParser(
        description="Backport PR to release branch. Will cherry pick the commit and create GitHub PR."
    )
    parser.add_argument("release", type=str, help="Release to backport to")
    parser.add_argument("commit_or_pr", type=str, help="Commit ID or PR number to backport")
    return parser.parse_args()


def main():
    args = parse_args()

    repo = Repo(".")
    commit, pr = get_commit_and_pr(repo, args.commit_or_pr)

    branch_name = f"backport-{pr}-{args.release}"

    release_branch = f"release-{args.release}"

    if branch_name in repo.heads:
        print(f"Not creating branch {branch_name} because it already exists")
        repo.heads[branch_name].checkout()
    else:
        # Checkout release branch
        repo.heads[release_branch].checkout()

        # Make sure we have the latest release of the release branch
        repo.remotes["origin"].pull()

        new_branch = repo.create_head(branch_name)
        new_branch.checkout()

        repo.git.cherry_pick(commit)

    repo.remotes["origin"].push()

    with (Path.home() / ".config" / "gh" / "hosts.yml").open() as f:
        token = yaml.safe_load(f.read())["github.com"]["oauth_token"]

    g = Github(token)

    # Remote can be of the form https://github.com/user/repo.git or git@github.com:user/repo.git
    github_repo = repo.remotes["origin"].url.replace("https://github.com/", "").replace("git@github.com:", "")
    github_repo = github_repo.removesuffix(".git")

    repo = g.get_repo(github_repo)

    orig_title = commit.message.split("\n")[0]
    title = orig_title.replace(f"#{pr}", args.release)
    body = f"Backport of #{pr} to release {args.release}"

    created_pr = repo.create_pull(title=title, body=body, head=branch_name, base=release_branch)

    print("Successfully created PR:", created_pr.html_url)


if __name__ == "__main__":
    main()
