#!/usr/bin/env python
from __future__ import print_function

import sys
import argparse
import itertools
from datetime import datetime, timedelta
from backports import statistics

import iso8601
from urlobject import URLObject

from jreport.util import paginated_get

DEBUG = False

REPOS = (
    # owner, repo, label to indicate external contribution
    ("edx", "edx-platform", "open-source-contribution"),
    ("edx", "configuration", "open-source-contribution"),
)


def get_duration_data(owner="edx", repo="edx-platform", since=None,
                      external_label="open-source-contribution"):
    """
    Return four lists of data, where each list contains only timedelta objects:
      age of internal open pull requests (all)
      age of external open pull requests (all)
      age of internal closed pull requests (since the `since` value)
      age of external closed pull requests (since the `since` value)

    These lists are organized into an object that categorizes the lists
    by position and state.
    """
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
        if not issue['pull_request']['url']:
            continue

        label_names = [label["name"] for label in issue["labels"]]

        if external_label in label_names:
            position = "external"
        else:
            position = "internal"

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
    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = datetime.now() - timedelta(days=args.since)
        # make it a date, not a datetime
        since = since.date()

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
        repo_durations = get_duration_data(owner, repo, since, label)
        for state in ("open", "closed"):
            for position in ("external", "internal"):
                durations[state][position].extend(repo_durations[state][position])

    for state in ("open", "closed"):
        for position in ("external", "internal"):
            seconds = [d.total_seconds() for d in durations[state][position]]
            median_seconds = round(statistics.median(seconds))
            median_duration = timedelta(seconds=median_seconds)
            if state == "open":
                population = "all"
            elif since:
                population = "since {date}".format(date=since)
            print("median {position} {state} ({population}): {duration}".format(
                position=position, state=state, population=population,
                duration=median_duration
            ))

if __name__ == "__main__":
    main(sys.argv)
