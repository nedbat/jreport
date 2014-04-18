#!/usr/bin/env python
from __future__ import print_function

import argparse
import datetime
import more_itertools
import operator
import sys

from urlobject import URLObject
import yaml
import requests

import jreport
from jreport.util import paginated_get

ISSUE_FMT = "{number:5d:white:bold} {user.login:>17s:cyan} {comments:3d:red}  {title:.100s} {pull.commits}c{pull.changed_files}f {pull.additions:green}+{pull.deletions:red}- {state:white:negative} {updated_at:ago:white} {created_at:%b %d:yellow}"
COMMENT_FMT = "{:31}{user.login:cyan} {created_at:%b %d:yellow}  \t{body:oneline:.100s:white}"


def show_pulls(jrep, labels=None, show_comments=False, state="open", since=None, org=False):
    labels = labels or []

    url = URLObject("https://api.github.com/repos/edx/edx-platform/issues")
    if labels:
        url = url.set_query_param('labels', ",".join(labels))
    if since:
        url = url.set_query_param('since', since.isoformat())
    if state:
        url = url.set_query_param('state', state)
    url = url.set_query_param('sort', 'updated')

    try:
        with open("mapping.yaml") as fmapping:
            user_mapping = yaml.load(fmapping)
        def_org = "other"
    except IOError:
        user_mapping = {}
        def_org = "---"

    issues = (jreport.JObj(issue) for issue in paginated_get(url))
    if org:
        # exhaust the generator
        issues = list(issues)
        # look up each user's organization
        for issue in issues:
            issue['org'] = user_mapping.get(issue["user.login"], {}).get("institution", def_org)
        # re-sort issues based on user organizations
        issues = sorted(issues, key=operator.itemgetter("org"))

    category = None
    for index, issue in enumerate(issues):
        pr_url = issue.get('pull_request', {}).get('url')
        if not pr_url:
            # We only want pull requests.
            continue
        issue['pull'] = requests.get(pr_url).json()
        if issue.get("org") != category:
            # new category! print category header
            category = issue["org"]
            print("-- {category} ----".format(category=category))
        print(issue.format(ISSUE_FMT))
        if show_comments:
            comments_url = URLObject(issue['comments_url'])
            comments_url = comments_url.set_query_param("sort", "created")
            comments_url = comments_url.set_query_param("direction", "desc")
            comments = paginated_get(comments_url)
            last_five_comments = reversed(more_itertools.take(5, comments))
            for comment in last_five_comments:
                print(comment.format(COMMENT_FMT))

    # index is now set to the total number of pull requests
    print()
    print("{num} pull requests".format(num=index))


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("-a", "--all-labels", action='store_true',
        help="Show all open pull requests, else only open-source",
        )
    parser.add_argument("--closed", action='store_true',
        help="Include closed pull requests",
        )
    parser.add_argument("--comments", dest="show_comments", action='store_true',
        help="Also show 5 most recent comments",
        )
    parser.add_argument("--debug",
        help="See what's going on.  DEBUG=http or json are fun.",
        )
    parser.add_argument("--org", action='store_true',
        help="Include and sort by affiliation",
        )
    parser.add_argument("--since", metavar="DAYS", type=int,
        help="Include pull requests active in the last DAYS days.",
        )

    args = parser.parse_args(argv[1:])

    labels = []
    if not args.all_labels:
        labels.append("open-source-contribution")

    if args.closed:
        state = "all"
    else:
        state = "open"

    since = None
    if args.since:
        since = datetime.datetime.now() - datetime.timedelta(days=args.since)

    jrep = jreport.JReport(debug=args.debug)
    show_pulls(
        jrep,
        labels=labels,
        show_comments=args.show_comments,
        state=state,
        since=since,
        org=args.org,
    )


if __name__ == "__main__":
    main(sys.argv)
