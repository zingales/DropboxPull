import requests
from lxml import html
import re


class SplInterface(object):

    def __init__(self, email):
        self.email = email
        self.session = requests.Session()

    def login(self, user_name, password):
        login_url = "https://seattle.bibliocommons.com/user/login?destination=/"

        r = self.session.get(login_url)
        doc = html.fromstring(r.text)

        input = doc.xpath('//input[@name="authenticity_token"]')[0]
        auth_token = input.value

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
        doc = html.fromstring(r.json()['html'])
        auth_token = doc.xpath("//input[@name='authenticity_token']")[0].value

        placeHold_url = "https://seattle.bibliocommons.com/holds/place_digital_hold/{book_id}?utf8=✓&authenticity_token={auth_token}=&service_type=OverDriveAPI&auto_checkout=1&digital_email={email}&hold_button_bundle=block_button"

        url = placeHold_url.format(
            book_id=book_id, auth_token=auth_token, email=self.email)

        r = self.session.get(url)


def get_book_id_from_url(url):
    regex = r"https:\/\/seattle.bibliocommons.com\/item\/show\/(\d+)"
    match = re.search(regex, url)
    if match:
        return match.group(1)

    return None


def test1(spli):
    spli.place_hold(123, "superauth")
