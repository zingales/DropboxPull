import os
import re
import json
from botocore.vendored import requests
# import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


class SplInterface(object):

    def __init__(self, email):
        self.email = email
        self.session = requests.Session()

    def login(self, user_name, password):
        login_url = "https://seattle.bibliocommons.com/user/login?destination=/"

        r = self.session.get(login_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        input = soup.find_all("input", {"name": "authenticity_token"})[0]
        auth_token = input["value"]

        # doc = html.fromstring(r.text)
        #
        # input = doc.xpath('//input[@name="authenticity_token"]')[0]
        # auth_token = input.value

        form_data = {
            "utf8": "✓",
            "authenticity_token": auth_token,
            "name": user_name,
            "user_pin": password,
            "local": "false"
        }

        r = self.session.post(login_url, data=form_data)

    def place_hold(self, book_id):
        # step 1 is we have to get the auth_token
        auth_token_url = "https://seattle.bibliocommons.com/holds/request_digital_title/{0}?hold_button_bundle=block_button".format(
            book_id)

        r = self.session.get(auth_token_url)

        soup = BeautifulSoup(r.json()['html'], 'html.parser')
        input = soup.find_all("input", {"name": "authenticity_token"})[0]
        auth_token = input["value"]

        placeHold_url = "https://seattle.bibliocommons.com/holds/place_digital_hold/{book_id}?utf8=✓&authenticity_token={auth_token}=&service_type=OverDriveAPI&auto_checkout=1&digital_email={email}&hold_button_bundle=block_button"

        url = placeHold_url.format(
            book_id=book_id, auth_token=auth_token, email=self.email)

        r = self.session.get(url)
        return r


def get_book_id_from_url(url):
    regex = r"https:\/\/seattle.bibliocommons.com\/item\/show\/(\d+)"
    match = re.search(regex, url)
    if match:
        return match.group(1)

    return None


slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]

email = os.environ["email"]
username = os.environ["username"]
password = os.environ["password"]

spli = SplInterface(email)
spli.login(username, password)

spli.place_hold(get_book_id_from_url(
    "https://seattle.bibliocommons.com/item/show/3061545030"))


def lambda_handler(event, context):
    if "challenge" in event:
        return event["challenge"]

    # logger.info("dis_what my event look like")
    # logger.info(event)
    url = event["text"]

    book_id = get_book_id_from_url(url)
    if book_id is None:
        return {
            'statusCode': 401,
            'body': json.dumps('Invalid spl url')
        }

    response = spli.place_hold(book_id)
    logger.info("dis_what my response looks like")
    logger.info(response)
    return {
        'statusCode': 200,
        'response_type': 'in_channel',
        'text': response.text,
    }
    # return spli.place_hold(book_id)
