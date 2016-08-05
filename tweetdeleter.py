#!/usr/bin/env python
 
import os
import sys
import argparse
import datetime 
import configparser
import time
import tweepy

class TweetDeleter():
    def __init__(self, args=None):
        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        if args:
            self.simulate = args.simulate
            self.verbose = args.verbose
            self.days_to_keep = args.days_to_keep
            self.liked_threshold = args.liked_threshold
            self.retweet_threshold = args.retweet_threshold
            self.tweet_ids_to_keep = args.tweet_ids_to_keep
            self.liked_ids_to_keep = args.liked_ids_to_keep
            self.tweet_keywords_to_keep = args.tweet_keywords_to_keep
            self.liked_keywords_to_keep = args.liked_keywords_to_keep
            if args.config_path == "settings.ini":
                self.config_path = os.path.join(self.script_dir, "settings.ini")
            else:
                self.config_path = args.config_path
        else:
            self.verbose = False
            self.simulate = False
            self.days_to_keep = -1
            self.tweet_ids_to_keep = []
            self.liked_ids_to_keep = []
            self.tweet_keywords_to_keep = []
            self.liked_keywords_to_keep = []
            self.liked_threshold = -1
            self.retweet_threshold = -1
            self.config_path = os.path.join(self.script_dir, "settings.ini")
        if not os.path.exists(self.config_path):
            self.create_config_template()
        self.authenticate_from_config()  # check required settings first
        if self.api:
            self.check_config()  # load values from config if not provided as args
            self.validate_values()

    def __repr__(self):
        rep_str = "<TweetDeleter object"
        dict_str = "\n\t".join(sorted(['{}={}'.format(k, v) for (k, v) in self.__dict__.items()]))
        rep_str = "{}\n\t{}".format(rep_str, dict_str)
        rep_str = "{}\n>".format(rep_str)
        return rep_str


    def check_config(self):
        # DAYS TO KEEP
        if self.days_to_keep < 0:
            v = self.load_from_config("DefaultValues", "DaysToKeep", -1)
            if v:
                self.days_to_keep = v
        # LIKE THRESHOLD
        if self.liked_threshold < 0:
            v = self.load_from_config("DefaultValues", "LikedThreshold", -1)
            if v:
                self.liked_threshold = v
        # RETWEET THRESHOLD
        if self.liked_threshold < 0:
            v = self.load_from_config("DefaultValues", "RetweetThreshold", -1)
            if v:
                self.retweet_threshold = v
        # TWEET IDs TO KEEP
        if not self.tweet_ids_to_keep:
            p = self.load_from_config("DefaultPaths", "TweetIDsPath", None)
            if p:
                self.tweet_ids_to_keep = self.list_loader(p, "tweet ID")
        # TWEET KWs TO KEEP
        if not self.tweet_keywords_to_keep:
            p = self.load_from_config("DefaultPaths", "TweetKeywordsPath", None)
            if p:
                self.tweet_keywords_to_keep = self.list_loader(p, "tweet keyword")
            

    def validate_values(self):
        # DAYS TO KEEP
        try: 
            self.days_to_keep = int(self.days_to_keep)
            if self.days_to_keep == -1:
                self.days_to_keep = 0
        except TypeError:
            print("Not a valid a valid number of days to keep, defaulting to 0 to ignore tweet age:\n{}".format(e))
            self.days_to_keep = 0
        else:
            self.cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=self.days_to_keep)
        # LIKE THRESHOLD
        try: 
            self.liked_threshold = int(self.liked_threshold)
        except TypeError:
            print("Povide a threshold for likes, defaulting to -1 to ignore number of likes:\n{}".format(e))
            self.liked_threshold = -1
        # RETWEET THRESHOLD
        try: 
            self.retweet_threshold = int(self.retweet_threshold)
        except TypeError:
            print("Provide a threshold for retweets, defaulting to -1 to ignore number of retweets:\n{}".format(e))
            self.retweet_threshold = -1

    def load_from_config(self, section, option, fail_val):
        config = configparser.SafeConfigParser()
        try:
            with open(self.config_path) as h:
                config.read_file(h)
        except IOError:
            return fail_val
        else:
            try:
                return config.get(section, option)
            except (configparser.NoSectionError, configparser.NoOptionError):
                print("Could not load option {} from section {}. Please check the information in your configuration file.".format(option, section))            
                return fail_val

    def list_loader(self, list_path, list_type):
        try:
            with open(list_path) as h:
                target = [l.strip("\n").strip() for l in h.readlines()]
                return target
        except IOError:
            print("Could not read {} file.".format(list_type))                
            return None

    def load_tweets_keywords_to_keep_from_file(self, str_path):
        self.tweet_keywords_to_keep = self.list_loader(str_path, "tweet keyword")

    def load_fav_ids_to_keep_from_file(self, id_path):
        self.list_loader(id_path, self.liked_ids_to_keep, "liked tweet ID")

    def load_fav_keywords_to_keep_from_file(self, str_path):
        self.list_loader(str_path, self.liked_keywords_to_keep, "liked tweet keyword")

    def set_days_to_keep(self, days_to_keep):
        try: 
            self.days_to_keep = int(days_to_keep)
        except TypeError:
            print("Please provide a number of days to keep, set to 0 to delete all:\n{}".format(e))
        else:
            self.cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=self.days_to_keep)
            print("Keeping tweets/likes from the last {} days. Set cutoff date to {} (UTC)".format(self.days_to_keep, self.cutoff_date))        

    def set_cutoff_date(self, cutoff_date):
        try:
            self.cutoff_date = datetime.datetime.strptime(cutoff_date, '%Y-%m-%d')
        except (TypeError, ValueError, NameError) as e:
            print("Could not set a cutoff date. Please provide a date as a YYYY-MM-DD string:\n{}".format(e))
        else:
            self.cutoff_date = datetime.datetime.strptime(cutoff_date, '%Y-%m-%d')
            print("Set cutoff date to {} (UTC)".format(self.cutoff_date))

    def authenticate_from_config(self, config_path=None):
        if config_path is not None:
            self.config_path = config_path
        config = configparser.SafeConfigParser()
        try:
            with open(self.config_path) as h:
                config.read_file(h)
        except IOError:
            print("Please specify a valid config file.")
        else:
            try:
                ck = config.get('Authentication', 'ConsumerKey')
                cs = config.get('Authentication', 'ConsumerSecret')
                at = config.get('Authentication', 'AccessToken')
                ats = config.get('Authentication', 'AccessTokenSecret')
            except (configparser.NoSectionError,):
                print("Please check the [Authentication] information in your configuration file.")
                self.api = None
            else:
                if all([ck, cs, at, ats]):
                    self.authenticate(ck, cs, at, ats)
                else:
                    self.api = None
                    print("Please check the options set under [Authentication] in your configuration file.")


    def authenticate(self, consumer_key, consumer_secret, access_token, access_token_secret):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth)
        try: 
            self.me = self.api.me()
            self.me = None  # only used to test access
        except tweepy.error.TweepError as e:
            print("Please check the authentication information:\n{}".format(e))
            self.api = None
            self.me = None

    def create_config_template(self):
        config = configparser.SafeConfigParser()
        config.optionxform = str
        config.add_section("Authentication")
        config.set("Authentication", "ConsumerKey", "")
        config.set("Authentication", "ConsumerSecret", "")
        config.set("Authentication", "AccessToken", "")
        config.set("Authentication", "AccessTokenSecret", "")
        config.add_section("DefaultValues")
        config.set("DefaultValues", "DaysToKeep", "")
        config.set("DefaultValues", "LikedThreshold", "")
        config.set("DefaultValues", "RetweetThreshold", "")
        config.add_section("DefaultPaths")
        config.set("DefaultPaths", "TweetIDsPath", "")
        config.set("DefaultPaths", "LikedIDsPath", "")
        config.set("DefaultPaths", "TweetKeywordsPath", "")
        config.set("DefaultPaths", "LikedKeywordsPath", "")
        print("Please specify a valid config file.")
        try:
            with open(self.config_path, "w") as h:
                config.write(h)
        except IOError:
            print("An empty configuration template has been created at {}".format(self.config_path))


    def contains_keywords_to_keep(self, tweet, fav=False):
        if fav:
            protected = any([True for s in self.liked_keywords_to_keep if s.lower() in tweet.text.lower()])
        else:
            protected = any([True for s in self.tweet_keywords_to_keep if s.lower() in tweet.text.lower()])
        return protected

    def is_protected_tweet(self, tweet):
        protected = False
        if tweet.id in self.tweet_ids_to_keep:
            protected = True
        elif tweet.created_at >= self.cutoff_date:
            protected = True
        elif self.contains_keywords_to_keep(tweet):
            protected = True
        elif self.liked_threshold != -1 and tweet.favorite_count >= self.liked_threshold:
            protected = True
        elif self.retweet_threshold != -1 and tweet.retweet_count >= self.retweet_threshold:
            protected = True
        return protected

    def is_protected_like(self, tweet):
        protected = False
        if tweet.id in self.liked_ids_to_keep:
            protected = True
        elif tweet.created_at >= self.cutoff_date:
            protected = True
        elif self.contains_keywords_to_keep(tweet, fav=True):
            protected = True
        elif self.liked_threshold != -1 and tweet.favorite_count >= self.liked_threshold:
            protected = True
        elif self.retweet_threshold != -1 and tweet.retweet_count >= self.retweet_threshold:
            protected = True
        return protected

    def delete_tweets(self):
        # rate limit appears to be 350 request / hour
        if not self.api:
            print("Could not authenticate. Please check the options set under [Authentication] in your configuration file.")
            return
        print("Deleting tweets older than {} (simulation={})".format(self.cutoff_date, self.simulate))
        if self.tweet_ids_to_keep:
            print("Keeping tweets with the following ids: {}".format(self.tweet_ids_to_keep))
        if self.tweet_keywords_to_keep:
            print("Keeping tweets containing the following keywords (case-insensitive): {}".format(self.tweet_keywords_to_keep))
        if self.retweet_threshold > -1:
            print("Keeping tweets with at least {} retweets".format(self.retweet_threshold))
        if self.liked_threshold > -1:
            print("Keeping tweets with at least {} likes".format(self.liked_threshold))
        timeline_tweets = tweepy.Cursor(self.api.user_timeline).items()
        deletion_count = 0
        ignored_count = 0
        try:
            for ind, tweet in enumerate(timeline_tweets):
                if not self.is_protected_tweet(tweet) and not self.simulate:
                    try:
                        self.api.destroy_status(tweet.id) 
                    except tweepy.error.TweepError as e:
                        print("\t#{}\tCOULD NOT DELETE {} ({})".format(ind, tweet.id, tweet.created_at))
                        print("\t", e)
                    else:
                        deletion_count += 1
                        if self.verbose:
                            print("\t#{}\tDELETED {} ({})".format(ind, tweet.id, tweet.created_at))
                else:                    
                    ignored_count += 1
                    if self.verbose:
                        print("\t#{}\tKEEPING {} ({})".format(ind, tweet.id, tweet.created_at))
        except tweepy.error.TweepError as e:
            print(e)
            print("Waiting 10 minutes, then starting over ({})".format(datetime.datetime.now()))
            time.sleep(600)
            self.delete_tweets()
        if not self.simulate:
            print("{} tweets were deleted. {} tweets were protected.".format(deletion_count, ignored_count))
        else:
            print("SIMULATION: {} tweets would be deleted. {} tweets would be protected.".format(deletion_count, ignored_count))


    def unlike_tweets(self):
        if not self.api:
            print("Could not authenticate. Please check the options set under [Authentication] in your configuration file.")
            return
        print("Unliking tweets older than {} (simulation={})".format(self.cutoff_date, self.simulate))
        if self.liked_ids_to_keep:
            print("Keeping liked tweets with the following ids: {}".format(self.liked_ids_to_keep))
        if self.liked_keywords_to_keep: 
            print("Keeping liked tweets containing the following keywords (case-insensitive): {}".format(self.liked_keywords_to_keep))

        likes = tweepy.Cursor(self.api.favorites).items()
        unliked_count = 0
        ignored_count = 0
        for ind, tweet in enumerate(likes):
            # Where tweets are not in save list and older than cutoff date
            if not self.is_protected_like(tweet) and not self.simulate:
                try:
                    self.api.destroy_favorite(tweet.id)
                except tweepy.error.TweepError as e:
                    print("\t#{}\tCOULD NOT UNLIKE {} ({})".format(ind, tweet.id, tweet.created_at))
                    print(e)
                else:
                    unliked_count += 1
                    if self.verbose:
                        print("\t#{}\tUNLIKED {} ({})".format(ind, tweet.id, tweet.created_at))
            else:
                ignored_count += 1
                if self.verbose:
                    print("\t#{}\tKEEPING {} ({})".format(ind, tweet.id, tweet.created_at))
        if not self.simulate:
            print("{} tweets were unliked. {} liked tweets were protected.".format(unliked_count, ignored_count))
        else:
            print("SIMULATION: {} tweets would be unliked. {} liked tweets would be protected.".format(unliked_count, ignored_count))

def comma_string_to_list(str):
   return str.split(',')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Delete or unlike tweets. Set other parameters via configuration file (default: "settings.ini" in script directory) or arguments. Set arguments will overrule the configuration file.')
    parser.add_argument("--delete", dest="delete_tweets", help="delete tweets.", action="store_true")
    parser.add_argument("--unlike", dest="unlike_tweets", help="unlike tweets.", action="store_true")
    parser.add_argument("--backup", dest="backup_tweets", help = "backup (liked) tweets to CSV file before deleting/unliking", action="store_true")
    parser.add_argument("--config", default="settings.ini", metavar="PATH", dest="config_path", help='Config path ', type=str, action="store")
    parser.add_argument("--simulate", dest="simulate", help = "only simulate the process", action="store_true")
    parser.add_argument("--verbose", dest="verbose", help = "enable detailed output", action="store_true")
    parser.add_argument("-D", default=-1, metavar="<n>", dest="days_to_keep", type=int, help="keep last <n> days of tweets/likes", action="store")
    parser.add_argument("-L", default=-1, metavar="<n>", dest="liked_threshold", type=int, help="keep tweets with >= <n> likes", action="store")
    parser.add_argument("-R", default=-1, metavar="<n>", dest="retweet_threshold", type=int, help="keep tweets with >= <n> retweets", action="store")
    parser.add_argument("--tweetids", default=[], metavar="", dest="tweet_ids_to_keep", type = comma_string_to_list, help="a string of comma-separated list of tweet ids to keep", action="store")
    parser.add_argument("--tweetkeys", default=[], metavar="", dest="tweet_keywords_to_keep", type = comma_string_to_list, help="a string of comma-separated list of keywords to identify tweets to keep", action="store")
    parser.add_argument("--likedids", default=[], metavar="", dest="liked_ids_to_keep", type = comma_string_to_list, help="a string of comma-separated tweet ids for liked tweets to keep.", action="store")
    parser.add_argument("--likedkeys", default=[], metavar="", dest="liked_keywords_to_keep", type = comma_string_to_list, help="a string of comma-separated list of keywords to identify liked tweets to keep (default: check config file)", action="store")
    
    args = parser.parse_args()
    print(args)
    td = TweetDeleter(args)
    print(td)
    """
    td.authenticate_from_config()
    td.delete_tweets()
    td.unlike_tweets()
    """