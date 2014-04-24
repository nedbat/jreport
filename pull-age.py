#!/usr/bin/env python
from __future__ import print_function

import argparse
import itertools
import sys
import yaml

from datetime import date, datetime, timedelta
from backports import statistics

import iso8601
from urlobject import URLObject

from jreport.util import paginated_get

DEBUG = False

REPOS = (
    # owner, repo, label to indicate external contribution
    ("edx", "edx-platform", "open-source-contribution"),
    #("edx", "configuration", "open-source-contribution"),
)


def get_internal_usernames():
    """
    Returns a set of the Github usernames that are associated with edX.
    """
    with open("mapping.yaml") as mapping_yaml:
        mapping = yaml.load(mapping_yaml)

    internal_usernames = set()
    for github_name, info in mapping.iteritems():
        if info.get("institution", "unknown") == "edX":
            internal_usernames.add(github_name)
    return internal_usernames


def get_duration_data(owner="edx", repo="edx-platform", since=None,
                      external_label="open-source-contribution", internal_usernames=None):
    """
    Return four lists of data, where each list contains only timedelta objects:
      age of internal open pull requests (all)
      age of external open pull requests (all)
      age of internal closed pull requests (since the `since` value)
      age of external closed pull requests (since the `since` value)

    These lists are organized into an object that categorizes the lists
    by position and state.
    """
    internal_usernames = internal_usernames or set()

    url = URLObject("https://api.github.com/repos/{owner}/{repo}/issues".format(
                    owner=owner, repo=repo))
    # two separate URLs, one for open PRs, the other for closed PRs
    open_url = url.set_query_param("state", "open")
    closed_url = url.set_query_param("state", "closed")
    if since:
        closed_url = closed_url.set_query_param('since', since.isoformat())

    durations = {
        "open": {
            "internal": [],
            "external": [],
        },
        "closed": {
            "internal": [],
            "external": [],
        }
    }

    open_issues_generator = itertools.izip(
        paginated_get(open_url),
        itertools.repeat("open")
    )
    closed_issues_generator = itertools.izip(
        paginated_get(closed_url),
        itertools.repeat("closed")
    )

    for issue, state in itertools.chain(open_issues_generator, closed_issues_generator):
        if not issue.get('pull_request', {}).get('url'):
            continue

        label_names = [label["name"] for label in issue["labels"]]

        if external_label and external_label in label_names:
            position = "external"
        else:
            if issue["user"]["login"] in internal_usernames:
                position = "internal"
            else:
                position = "external"

        created_at = iso8601.parse_date(issue["created_at"]).replace(tzinfo=None)
        if state == "open":
            closed_at = datetime.utcnow()
        else:
            closed_at = iso8601.parse_date(issue["closed_at"]).replace(tzinfo=None)
        duration = closed_at - created_at
        if DEBUG:
            print("{owner}/{repo}#{num}: {position} {state}".format(
                owner=owner, repo=repo, num=issue["number"],
                position=position, state=state
            ), file=sys.stderr)

        durations[state][position].append(duration)

    return durations


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("--since", metavar="DAYS", type=int, default=14,
        help="For closed issues, only include issues updated in the past DAYS days [%(default)d]"
    )
    parser.add_argument("--human", action="store_true",
        help="Human-readable output"
    )
    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = date.today() - timedelta(days=args.since)

    internal_usernames = get_internal_usernames()

    durations = {
        "open": {
            "internal": [],
            "external": [],
        },
        "closed": {
            "internal": [],
            "external": [],
        }
    }
    for owner, repo, label in REPOS:
        repo_durations = get_duration_data(owner, repo, since, label, internal_usernames)
        for state in ("open", "closed"):
            for position in ("external", "internal"):
                durations[state][position].extend(repo_durations[state][position])

    ss_friendly = ""
    for position in ("external", "internal"):
        for state in ("open", "closed"):
            seconds = [d.total_seconds() for d in durations[state][position]]
            if seconds:
                median_seconds = int(statistics.median(seconds))
                median_duration = timedelta(seconds=median_seconds)
            else:
                median_seconds = -1
                median_duration = "no data"
            population = "all"
            if state == "closed" and since:
                population = "since {date}".format(date=since)
            if args.human:
                print("median {position} {state} ({population}): {duration}".format(
                    position=position, state=state, population=population,
                    duration=median_duration
                ))
            else:
                ss_friendly += ",{},{}".format(len(seconds), median_seconds)

    if ss_friendly:
        print("when,repos,eopen,eopenage,eclosed,eclosedage,iopen,iopenage,iclosed,iclosedage")
        print("{:%m/%d/%Y},{}{}".format(date.today(), len(REPOS), ss_friendly))

if __name__ == "__main__":
    main(sys.argv)
