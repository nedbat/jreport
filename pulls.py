#!/usr/bin/env python
import argparse
import datetime
import itertools
import operator
import sys

import yaml

import jreport

ISSUE_FMT = "{number:5d:white:bold} {user.login:>17s:cyan} {comments:3d:red}  {title:.100s} {pull.commits}c{pull.changed_files}f {pull.additions:green}+{pull.deletions:red}- {state:white:negative} {updated_at:ago:white} {created_at:%b %d:yellow}"
COMMENT_FMT = "{:31}{user.login:cyan} {created_at:%b %d:yellow}  \t{body:oneline:.100s:white}"

def get_pulls(jrep, params):
    url = "https://api.github.com/repos/edx/edx-platform/issues"
    issues = jrep.get_json_array(url, params=params)
    issues = [iss for iss in issues if iss['pull_request.html_url']]
    return issues


def show_pulls(jrep, label=None, comments=False, states=None, since=None, org=False):
    params = {}
    if label:
        params['labels'] = label
    if since:
        params['since'] = since.isoformat()

    issues = []
    for state in (states or ["open"]):
        params['state'] = state
        issues.extend(get_pulls(jrep, params))

    try:
        with open("mapping.yaml") as fmapping:
            user_mapping = yaml.load(fmapping)
        def_org = "other"
    except IOError:
        user_mapping = {}
        def_org = "---"

    num_issues = len(issues)

    for issue in issues:
        issue['org'] = user_mapping.get(issue["user.login"], {}).get("institution", def_org)
        issue['pull'] = jrep.get_json_object("https://api.github.com/repos/edx/edx-platform/pulls/{}".format(issue["number"]))

    if org:
        issues = sorted(issues, key=operator.itemgetter("org"))
        grouped = itertools.groupby(issues, key=operator.itemgetter("org"))
    else:
        issues = sorted(issues, key=operator.itemgetter("updated_at"))
        grouped = [("all", issues)]

    for category, issues in grouped:
        print "-- {} ----".format(category)
        for issue in issues:
            print issue.format(ISSUE_FMT)
            if comments:
                comms = jrep.get_json_array(issue['comments_url'])
                for comment in comms[-5:]:
                    print comment.format(COMMENT_FMT)

    print "\n{} pull requests".format(num_issues)


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("-a", "--all", action='store_true',
        help="Show all open pull requests, else only open-source",
        )
    parser.add_argument("--closed", action='store_true',
        help="Include closed pull requests",
        )
    parser.add_argument("--comments", action='store_true',
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

    label = None
    if not args.all:
        label = "open-source-contribution"

    states = ["open"]
    if args.closed:
        states.append("closed")

    since = None
    if args.since:
        since = datetime.datetime.now() - datetime.timedelta(days=args.since)

    jrep = jreport.JReport(debug=args.debug)
    show_pulls(
        jrep,
        label=label,
        comments=args.comments,
        states=states,
        since=since,
        org=args.org,
    )


if __name__ == "__main__":
    main(sys.argv)
