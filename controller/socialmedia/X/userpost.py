import unicodedata
import pytz
import hashlib
import re
import json
import random
import string
import time

from pyquery import PyQuery
from requests.sessions import Session
from requests.cookies import RequestsCookieJar
from requests.exceptions import Timeout, ReadTimeout
from urllib.parse import urljoin, urlencode, quote
from faker import Faker
from datetime import datetime
from helper.html_parser import HtmlParser
from helper.utility import Utility


class Users:
    def __init__(self):
        self.session = Session()
        self.jar = RequestsCookieJar()
        self.fake = Faker()
        self.parser = HtmlParser()

        self.headers = dict()
        self.headers["Accept"] = "application/json, text/plain, */*"
        self.headers["Accept-Language"] = "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7"
        self.headers["Sec-Fetch-Dest"] = "empty"
        self.headers["Sec-Fetch-Mode"] = "cors"
        self.headers["Sec-Fetch-Site"] = "same-site"

    def __set_cookies(self, cookies):
        for cookie in cookies:
            if cookie["name"] == "msToken":
                msToken = cookie["value"]
            self.jar.set(
                cookie["name"],
                cookie["value"],
                domain=cookie["domain"],
                path=cookie["path"],
            )
        return self.jar

    def __processmedia(self, entry: dict = None) -> dict:
        if entry is not None:
            if not isinstance(entry, dict):
                raise TypeError(
                    "Invalid \"__processmedia\" parameter, value must be type dict, {} passed".format(
                        type(entry).__name__)
                )
            if isinstance(entry, dict):
                pass

        deeper = entry["content"]["itemContent"]["tweet_results"]["result"]
        id = deeper["rest_id"]
        unmention_data = deeper["unmention_data"]

        views = {
            key: value for key, value in deeper["views"].items()
            if key != "state"
        } if "views" in deeper else dict()

        self.__removeallentites(
            keyword="entities",
            datas=deeper
        )
        self.__removeallentites(
            keyword="extended_entities",
            datas=deeper
        )

        KEYS_REMOVE = [
            "conversation_id_str",
            "display_text_range",
            "is_quote_status",
            "possibly_sensitive",
            "possibly_sensitive_editable",
            "quoted_status_id_str",
            "quoted_status_permalink",
            "favorited",
            "retweeted",
            "user_id_str",
            "id_str"
        ]

        for key in list(
            self.__generatekey(
                datas=deeper,
                keys=KEYS_REMOVE,
                keyword="legacy"
            )
        ):
            del deeper["legacy"][key]

        for key, value in deeper["legacy"].items():
            if key == "created_at":
                initially = datetime.strptime(
                    value, "%a %b %d %H:%M:%S +0000 %Y"
                )
                new = initially.strftime("%Y-%m-%dT%H:%M:%S")
                deeper["legacy"].update({key: new})

        legacy = deeper["legacy"]

        data = {
            "id": id,
            "unmention_data": unmention_data,
            "views": views,
            "legacy": legacy
        }
        return data

    def __removeallentites(self, keyword: str, datas: dict) -> dict:
        if keyword is not None:
            if not isinstance(keyword, str):
                raise TypeError(
                    "Invalid \"__removeallentites\" parameter, value must be type str, {} passed".format(
                        type(keyword).__name__)
                )
            if isinstance(keyword, str):
                pass
        if datas is not None:
            if not isinstance(datas, dict):
                raise TypeError(
                    "Invalid \"__removeallentites\" parameter, value must be type dict, {} passed".format(
                        type(datas).__name__)
                )
            if isinstance(datas, dict):
                pass

        KEYS_REMOVE = [
            "id_str",
            "indices",
            "media_key",
            "ext_media_availability",
            "features",
            "sizes",
            "original_info"
        ]
        if keyword in datas["legacy"]:
            if "media" in datas["legacy"][keyword]:
                for e_media in datas["legacy"][keyword]["media"]:
                    for key in list(self.__generatekey(
                        datas=e_media,
                        keys=KEYS_REMOVE
                    )):
                        del e_media[key]
                        url = e_media["url"]

                for key, value in datas["legacy"].items():
                    if key == "full_text":
                        datas["legacy"].update(
                            {
                                key: value.replace(url, "").rstrip()
                            }
                        )
                return
        return

    def __generatekey(self, datas: dict, keys: list, keyword: str = None):
        if datas is not None:
            if not isinstance(datas, dict):
                raise TypeError(
                    "Invalid \"__generatekey\" parameter, value must be type dict, {} passed".format(
                        type(datas).__name__)
                )
            if isinstance(datas, dict):
                pass
        if keys is not None:
            if not isinstance(keys, list):
                raise TypeError(
                    "Invalid \"__generatekey\" parameter, value must be type list, {} passed".format(
                        type(keys).__name__)
                )
            if isinstance(keys, list):
                pass
        if keyword is not None:
            if not isinstance(keyword, str):
                raise TypeError(
                    "Invalid \"__removeallentites\" parameter, value must be type str, {} passed".format(
                        type(keyword).__name__)
                )
            if isinstance(keyword, str):
                pass

        if keyword:
            for key in datas[keyword]:
                if key in keys:
                    yield key
        for key in datas:
            if key in keys:
                yield key

    def __replacechar(self, text: str, replacement: str):
        pattern = re.compile(r'_(.*?)\.jpg')
        matches = pattern.search(
            string=text.split("/")[-1]
        )
        if matches:
            replace = matches.group(1)
            result = text.replace(replace, replacement)
            return result
        return text

    def __guest_token(self, cookies=None):
        user_agent = self.fake.user_agent()
        auth = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        url = "https://api.twitter.com/1.1/guest/activate.json"
        self.headers["User-Agent"] = user_agent
        self.headers["Authorization"] = auth
        resp = self.session.post(
            url=url,
            headers=self.headers,
            cookies=cookies,
            timeout=60
        )
        status_code = resp.status_code
        content = resp.json()["guest_token"]
        if status_code == 200:
            self.headers.update({
                "X-Guest-Token": content
            })
        return self.headers["X-Guest-Token"]

    def profile(self, screen_name: str = None, proxy=None, cookies=None, **kwargs) -> dict:
        """Function to retrieve user profile details from specified screen_name. The result is a data dictionary.

        Arguments:
        - screen_name = username on twitter.
        """
        user_agent = self.fake.user_agent()
        if cookies:
            cookies = self.__set_cookies(cookies=cookies)
        if screen_name is not None:
            if not isinstance(screen_name, str):
                raise TypeError(
                    "Invalid \"profile\" parameter, value must be type str, {} passed".format(
                        type(screen_name).__name__)
                )
            if isinstance(screen_name, str):
                pass

        params = {
            "variables": {
                "screen_name": screen_name,
                "withSafetyModeUserFields": True
            },
            "features": {
                "hidden_profile_likes_enabled": True,
                "hidden_profile_subscriptions_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_is_identity_verified_enabled": True,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "responsive_web_twitter_article_notes_tab_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            },
            "fieldToggles": {
                "withAuxiliaryUserLabels": True
            }
        }
        for key in params:
            params.update({key: Utility.convertws(params[key])})

        variables = quote(params["variables"])
        features = quote(params["features"])
        fieldToggles = quote(params["fieldToggles"])
        url = "https://api.twitter.com/graphql/NimuplG1OB7Fd2btCLdBOw/UserByScreenName?variables={variables}&features={features}&fieldToggles={fieldToggles}".format(
            variables=variables,
            features=features,
            fieldToggles=fieldToggles
        )
        self.headers["User-Agent"] = user_agent
        self.headers["X-Guest-Token"] = self.__guest_token()
        resp = self.session.request(
            method="GET",
            url=url,
            timeout=60,
            proxies=proxy,
            headers=self.headers,
            cookies=cookies,
            **kwargs
        )
        status_code = resp.status_code
        content = resp.content
        if status_code == 200:
            response = content.decode('utf-8')
            data = json.loads(response)
            result: dict = data["data"]["user"]
            for key, value in result["result"]["legacy"].items():
                if key == "profile_image_url_https":
                    result["result"]["legacy"].update(
                        {
                            key: self.__replacechar(
                                value,
                                "400x400"
                            )
                        }
                    )
                if key == "created_at":
                    initially = datetime.strptime(
                        result["result"]["legacy"][key], "%a %b %d %H:%M:%S +0000 %Y"
                    )
                    new = initially.strftime("%Y-%m-%dT%H:%M:%S")
                    result["result"]["legacy"].update({key: new})
            return result
        else:
            raise Exception(
                f"Error! status code {resp.status_code} : {resp.reason}")

    def userspost(self, userId: int | str = None, proxy=None, cookies=None, **kwargs) -> dict:
        """The function to retrieve details from a user's post uses the userId input obtained when retrieving user profile details.
        The result is a data dictionary.

        Arguments:
        - userId = ID of the Twitter user.
        """
        user_agent = self.fake.user_agent()
        if cookies:
            cookies = self.__set_cookies(cookies=cookies)
        if userId is not None:
            if not isinstance(userId, (int | str)):
                raise TypeError(
                    "Invalid \"recomendation\" parameter, value must be type str|int, {} passed".format(
                        type(userId).__name__)
                )
            if isinstance(userId, (int | str)):
                userId = int(userId)

        params = {
            "variables": {
                "userId": userId,
                "count": 20,
                "includePromotedContent": True,
                "withQuickPromoteEligibilityTweetFields": True,
                "withVoice": True,
                "withV2Timeline": True
            },
            "features": {
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "c9s_tweet_anatomy_moderator_badge_enabled": True,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "rweb_video_timestamps_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False
            }
        }
        for key in params:
            params.update({key: Utility.convertws(params[key])})

        variables = quote(params["variables"])
        features = quote(params["features"])
        url = "https://api.twitter.com/graphql/V1ze5q3ijDS1VeLwLY0m7g/UserTweets?variables={variables}&features={features}".format(
            variables=variables,
            features=features
        )
        self.headers["User-Agent"] = user_agent
        self.headers["X-Guest-Token"] = self.__guest_token()
        resp = self.session.request(
            method="GET",
            url=url,
            timeout=60,
            proxies=proxy,
            headers=self.headers,
            cookies=cookies,
            **kwargs
        )
        status_code = resp.status_code
        content = resp.content
        if status_code == 200:
            response = content.decode('utf-8')
            data = json.loads(response)
            return data
        else:
            raise Exception(
                f"Error! status code {resp.status_code} : {resp.reason}")

    def media(self, screen_name: str = None) -> dict:
        """The function to retrieve details from the user's post uses the screen_name input. The result is a data dictionary.

        Arguments:
        - screen_name = username on twitter.
        """
        if screen_name is not None:
            if not isinstance(screen_name, str):
                raise TypeError(
                    "Invalid \"media\" parameter, value must be type str, {} passed".format(
                        type(screen_name).__name__)
                )
            if isinstance(screen_name, str):
                pass

        try:
            profile = self.profile(screen_name=screen_name)
            userId = profile["result"]["rest_id"]
            raw = self.userspost(userId=userId)
            instructions = raw["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
            datas = []
            for index, value in enumerate(instructions):
                if isinstance(value, dict) and value["type"] == "TimelinePinEntry":
                    deep = instructions[index]

                    entry = deep["entry"]
                    data = self.__processmedia(entry=entry)
                    datas.append(data)

                if isinstance(value, dict) and value["type"] == "TimelineAddEntries":
                    deep = instructions[index]

                    for entry in deep["entries"]:
                        data = self.__processmedia(entry=entry)
                        datas.append(data)
            result = {
                "result": datas
            }
            return result

        except Exception as e:
            raise Exception(
                f"Error! message: {e}"
            )

    def recomendation(self, userId: str | int = None, limit: str | int = None, proxy=None, cookies=None) -> dict:
        """Function to retrieve recommended Twitter users according to the userId entered. The result is a data dictionary.

        Arguments:
        - userId = ID of the Twitter user.
        - limit = number of recommended users.
        """
        if userId is not None:
            if not isinstance(userId, (int | str)):
                raise TypeError(
                    "Invalid \"recomendation\" parameter, value must be type str|int, {} passed".format(
                        type(userId).__name__)
                )
            if isinstance(userId, (int | str)):
                userId = int(userId)
        if limit is not None:
            if not isinstance(limit, (int | str)):
                raise TypeError(
                    "Invalid \"recomendation\" parameter, value must be type str|int, {} passed".format(
                        type(limit).__name__)
                )
            if isinstance(limit, (int | str)):
                limit = int(limit)

        user_agent = self.fake.user_agent()
        if cookies:
            cookies = self.__set_cookies(cookies=cookies)
        params = {
            "include_profile_interstitial_type": 1,
            "include_blocking": 1,
            "include_blocked_by": 1,
            "include_followed_by": 1,
            "include_want_retweets": 1,
            "include_mute_edge": 1,
            "include_can_dm": 1,
            "include_can_media_tag": 1,
            "include_ext_has_nft_avatar": 1,
            "include_ext_is_blue_verified": 1,
            "include_ext_verified_type": 1,
            "include_ext_profile_image_shape": 1,
            "skip_status": 1,
            "pc": True,
            "display_location": "profile_accounts_sidebar",
            "limit": limit,
            "user_id": userId,
            "ext": "mediaStats,highlightedLabel,hasNftAvatar,voiceInfo,birdwatchPivot,superFollowMetadata,unmentionInfo,editControl"
        }
        url = "https://api.twitter.com/1.1/users/recommendations.json"
        self.headers["User-Agent"] = user_agent
        self.headers["X-Guest-Token"] = self.__guest_token()
        resp = self.session.get(
            url=url,
            params=params,
            headers=self.headers,
            cookies=cookies,
            timeout=60,
            proxies=proxy
        )
        status_code = resp.status_code
        content = resp.content
        if status_code == 200:
            response = content.decode('utf-8')
            datas = json.loads(response)

            KEYS_REMOVE = [
                "protected",
                "fast_followers_count",
                "normal_followers_count",
                "utc_offset",
                "time_zone",
                "geo_enabled",
                "verified",
                "contributors_enabled",
                "is_translator",
                "is_translation_enabled",
                "profile_background_color",
                "profile_background_tile",
                "profile_link_color",
                "profile_sidebar_border_color",
                "profile_sidebar_fill_color",
                "profile_text_color",
                "profile_use_background_image",
                "default_profile",
                "default_profile_image",
                "pinned_tweet_ids",
                "pinned_tweet_ids_str",
                "has_custom_timelines",
                "can_dm",
                "can_media_tag",
                "following",
                "follow_request_sent",
                "notifications",
                "muting",
                "blocking",
                "blocked_by",
                "want_retweets",
                "advertiser_account_type",
                "advertiser_account_service_levels",
                "analytics_type",
                "profile_interstitial_type",
                "business_profile_state",
                "translator_type",
                "withheld_in_countries",
                "followed_by",
                "ext_highlighted_label",
                "ext_is_blue_verified",
                "require_some_consent"
            ]

            for data in datas:
                deeper = data["user"]
                for key in list(
                    self.__generatekey(
                        datas=deeper,
                        keys=KEYS_REMOVE
                    )
                ):
                    del deeper[key]

                for key, value in deeper.items():
                    if key == "created_at":
                        initially = datetime.strptime(
                            value, "%a %b %d %H:%M:%S +0000 %Y"
                        )
                        new = initially.strftime("%Y-%m-%dT%H:%M:%S")
                        deeper.update({key: new})

            result = {
                "result": datas
            }
            return result
        else:
            raise Exception(
                f"Error! status code {resp.status_code} : {resp.reason}")


if __name__ == "__main__":
    sb = Users()
