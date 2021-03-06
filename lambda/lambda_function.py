"""
Slack chat-bot Lambda handler.
"""

import os
import logging
import urllib
import pymysql
import json

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)

# Grab the Bot OAuth token from the environment.
BOT_TOKEN = os.environ["BOT_TOKEN"]

# Define the URL of the targeted Slack API resource.
# We'll send our replies there.
SLACK_URL = "https://slack.com/api/chat.postMessage"

slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]

rds_host = os.environ["rds_host"]
user = os.environ["db_user"]
password = os.environ["db_password"]
db_name = os.environ["db_name"]


class RDSInterface(object):

    def __init__(self, rds_host, user, password, db_name):
        self.conn = pymysql.connect(rds_host, user=user,
                                    passwd=password, db=db_name, connect_timeout=5)

    def query_name(self, name_substring):
        cur = self.conn.cursor()
        sql = "select * from raw_dropbox where name like %s OR series like %s"

        cur.execute(sql, [('%' + name_substring + '%'),
                          ('%' + name_substring + '%')])

        data = cur.fetchall()
        cur.close()

        return data


try:
    rdsi = RDSInterface(rds_host, user,
                        password, db_name)
except Exception as e:
    logger.error(e)
    logger.error(
        "ERROR: Unexpected error: Could not connect to MySql instance.")
logger.info("SUCCESS: Connection to RDS mysql instance succeeded")


def formatQueryOutput(tuples):
    if tuples is None or len(tuples) == 0:
        return "no books found"

    output = ""
    for tuple in tuples:
        output += "Book: {2}, Series: {1}, link: {4}\n".format(*tuple)

    return output


def lambda_handler(data, context):
    """Handle an incoming HTTP request from a Slack chat-bot.
    """

    if "challenge" in data:
        return data["challenge"]

    # Grab the Slack event data.
    slack_event = data['event']

    # We need to discriminate between events generated by
    # the users, which we want to process and handle,
    # and those generated by the bot.
    if "bot_id" in slack_event:
        logging.warn("Ignore bot event")
    else:
        # Get the text of the message the user sent to the bot,
        # and reverse it.
        text = slack_event["text"]
        reversed_text = formatQueryOutput(rdsi.query_name(text))

        # Get the ID of the channel where the message was posted.
        channel_id = slack_event["channel"]

        # We need to send back three pieces of information:
        #     1. The reversed text (text)
        #     2. The channel id of the private, direct chat (channel)
        #     3. The OAuth token required to communicate with
        #        the API (token)
        # Then, create an associative array and URL-encode it,
        # since the Slack API doesn't not handle JSON (bummer).
        data = urllib.parse.urlencode(
            (
                ("token", BOT_TOKEN),
                ("channel", channel_id),
                ("text", reversed_text)
            )
        )
        data = data.encode("ascii")

        # Construct the HTTP request that will be sent to the Slack API.
        request = urllib.request.Request(
            SLACK_URL,
            data=data,
            method="POST"
        )
        # Add a header mentioning that the text is URL-encoded.
        request.add_header(
            "Content-Type",
            "application/x-www-form-urlencoded"
        )

        # Fire off the request!
        urllib.request.urlopen(request).read()

    # Everything went fine.
    return "200 OK"
