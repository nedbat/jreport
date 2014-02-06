import argparse
import operator
import sys

import jreport

ISSUE_FMT = "{number:5d:white:bold} {user.login:>17s:cyan} {comments:3d:red}  {title:.100s}  - {updated_at:ago:white} {created_at:%b %d:yellow}"
COMMENT_FMT = "{:31}{user.login:cyan} {created_at:%b %d:yellow}  \t{body:oneline:.100s:white}"

def show_pulls(jrep, label=None, comments=False):
    url = "https://api.github.com/repos/edx/edx-platform/issues"
    params = {}
    if label:
        params['labels'] = label

    issues = jrep.get_json_array(url, params=params)
    issues = [iss for iss in issues if iss['pull_request.html_url']]
    issues = sorted(issues, key=operator.itemgetter("updated_at"))

    for issue in issues:
        print issue.format(ISSUE_FMT)
        if comments:
            comms = jrep.get_json_array(issue['comments_url'])
            for comment in comms[-5:]:
                print comment.format(COMMENT_FMT)

    print "\n{} pull requests".format(len(issues))


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("-a", "--all", action='store_true')
    parser.add_argument("-c", "--comments", action='store_true')
    parser.add_argument("--debug")

    args = parser.parse_args(argv[1:])

    kwargs = {}

    if not args.all:
        kwargs['label'] = "open-source-contribution"

    kwargs['comments'] = args.comments

    jrep = jreport.JReport(debug=args.debug)
    show_pulls(jrep, **kwargs)

if __name__ == "__main__":
    main(sys.argv)
