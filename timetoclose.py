#!/usr/bin/env python
from __future__ import print_function

import sys
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

import iso8601
from urlobject import URLObject

from jreport.util import paginated_get

segments = [
    ("less than thiry minutes", timedelta(0), timedelta(minutes=30)),
    ("half an hour to one hour", timedelta(minutes=30), timedelta(hours=1)),
    ("one to two hours", timedelta(hours=1), timedelta(hours=2)),
    ("two to four hours", timedelta(hours=2), timedelta(hours=4)),
    ("four to eight hours", timedelta(hours=4), timedelta(hours=8)),
    ("eight hours to one day", timedelta(hours=8), timedelta(days=1)),
    ("one to two days", timedelta(days=1), timedelta(days=2)),
    ("two to three days", timedelta(days=2), timedelta(days=3)),
    ("three to five days", timedelta(days=3), timedelta(days=5)),
    ("five to eight days", timedelta(days=5), timedelta(days=8)),
    ("eight days to two weeks", timedelta(days=8), timedelta(weeks=2)),
    ("two weeks to four weeks", timedelta(weeks=2), timedelta(weeks=4)),
    ("four weeks to six weeks", timedelta(weeks=4), timedelta(weeks=6)),
    ("six weeks to eight weeks", timedelta(weeks=6), timedelta(weeks=8)),
    ("two to three months", timedelta(weeks=8), timedelta(weeks=12)),
    ("three to six months", timedelta(weeks=12), timedelta(weeks=24)),
    ("more than six months", timedelta(weeks=24), timedelta.max),
]


def get_segment(duration):
    for text, low, high in segments:
        if low <= duration < high:
            return text
    return "unknown"


def get_duration_info(since=None, labels=None, pull_requests=False):
    labels = labels or []

    url = URLObject("https://api.github.com/repos/edx/edx-platform/issues")
    # we only care about closed PRs for now
    url = url.set_query_param('state', 'closed')
    if labels:
        url = url.set_query_param('labels', ",".join(labels))
    if since:
        url = url.set_query_param('since', since.isoformat())

    counter = defaultdict(list)
    for issue in paginated_get(url):
        if pull_requests and not issue['pull_request']['url']:
            continue
        num = issue['number']
        created_at = iso8601.parse_date(issue["created_at"])
        closed_at = iso8601.parse_date(issue["closed_at"])
        duration = closed_at - created_at
        segment = get_segment(duration)
        counter[segment].append(num)

    return counter


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("-a", "--all-labels", action='store_true',
        help="Show all issues, else only open-source",
    )
    parser.add_argument("--since", metavar="DAYS", type=int,
        help="Only include issues created in the past DAYS days"
    )
    parser.add_argument('--pr', '--pull-requests', action='store_true', dest="pull_requests",
        help="Only show issues that are pull requests"
    )
    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = datetime.now() - timedelta(days=args.since)

    labels = []
    if not args.all_labels:
        labels.append('open-source-contribution')

    durations = get_duration_info(since, labels, args.pull_requests)

    for text, _, _ in segments:
        if durations[text]:
            print("{text}: {num}".format(text=text, num=len(durations[text])))

if __name__ == "__main__":
    main(sys.argv)
