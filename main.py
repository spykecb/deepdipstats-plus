import requests
import os
import json
import pandas as pd
from datetime import datetime
import pytz
import logging
from twitch_url import TwitchUrl
import argparse

parser = argparse.ArgumentParser(
                    prog='deepdip-stats')

parser.add_argument('--enable-twitch-url', action=argparse.BooleanOptionalAction)
parser.add_argument(
    '-p', '--players',
    nargs='+', 
    default=[
        "BrenTM",
        "Larstm",
        "Hazardu.",
        "eLconn21",
        "Schmaniol",
    ],
    help="List of players"
)
args = parser.parse_args()

API_URL = "https://www.deepdipstats.com/api/playerstats?username="
FALL_THRESHOLD = 90
STEP_THRESHOLD = 2
FALL_STEP_THRESHOLD = 3
RESULT_PATH = "result/"

result = {
    "user":[],
    "day":[],
    "floor":[],
    "floor_result":[],
    "timestamp":[],
    "on_stream":[]
}

with open("tmuser_to_twitchuser.json", "r") as f:
    tmuser_to_twitchuser = json.load(f)

floor_heights = {
    0 : 0,
    1 : 100,
    2 : 209,
    3 : 314,
    4 : 420,
    5 : 520,
    6 : 620,
    7 : 740,
    8 : 815,
    9 : 937,
    10 : 1045,
    11 : 1150,
    12 : 1270,
    13 : 1378,
    14 : 1490,
    15 : 1584,
    16 : 1688,
    17 : 1800,
    18 : 2000
}


enable_filter_from_day = True
filter_from_day = "Day 26"

enable_partial_completion = True
enable_twitch_url = args.enable_twitch_url
debug_mode = False
debug_limit_user = ["Schmaniol"]
debug_limit_day = ["Day 36"]

open('debug.log', 'w').close()
logging.basicConfig(filename="debug.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)
                    

fall_to_floor_counter = dict()

def get_curr_floor(height):
    for i in range(18):
        if i not in floor_heights or i+1 not in floor_heights:
            continue
        if height > floor_heights[i] and height < floor_heights[i+1]:
            return i
    return -1

def convert_to_jst(datetime_str):
    datetime_obj = datetime.strptime(datetime_str, "%m/%d, %I:%M %p")

    datetime_obj = datetime_obj.replace(year=datetime.now().year)

    datetime_obj_utc = pytz.utc.localize(datetime_obj)

    jst = pytz.timezone('Asia/Tokyo')
    datetime_obj_jst = datetime_obj_utc.astimezone(jst)
    return datetime_obj_jst.strftime("%Y/%m/%d, %I:%M %p")

def parse_api_data():
    twitch_url = TwitchUrl()
    if enable_twitch_url:
        twitch_url.init()
    for user in args.players:
        if debug_mode and user not in debug_limit_user:
            continue
        analyze_user(user, twitch_url)


def analyze_user(user, twitch_url_obj: TwitchUrl):
    url = f"{API_URL}{user}"
    data = requests.get(url).json()
    data = merge_data_with_local(data, user)
    prev_height = 0
    prev_floor = -1
    prev_prev_floor = -1
    step_idx_since_new_floor_up = 0
    step_idx_since_new_floor_down = 0
    for dailyData in data["dailyData"]:
        if debug_mode and dailyData not in debug_limit_day:
            continue
        if enable_filter_from_day and dailyData < filter_from_day:
            logging.info(f"Skipping {dailyData}")
            continue
        logging.info(f"=========={dailyData}==========")
        step_idx_since_day = 0
        for heightData in data["dailyData"][dailyData]:
            if step_idx_since_day == 0 and heightData["height"] < 200:
                prev_height = 0
                prev_floor = -1
                step_idx_since_new_floor_up = 0
                step_idx_since_new_floor_down = 0
            step_idx_since_day += 1
            step_idx_since_new_floor_up += 1 
            new_height = heightData["height"]
            ts = heightData["timestamp"]
            ts_jst = convert_to_jst(ts)
            twitch_url = twitch_url_obj.get_video_url(tmuser_to_twitchuser[user], ts) if enable_twitch_url and user in tmuser_to_twitchuser else None
            on_stream = twitch_url is not None
            prev_step_floor = get_curr_floor(prev_height)
            curr_step_floor = get_curr_floor(new_height)
            this_result = -1
            floor_data = -1
            if curr_step_floor != prev_step_floor:
                step_idx_since_new_floor_down = 0
            if curr_step_floor < prev_floor:
                step_idx_since_new_floor_down += 1
                # print(f"step_idx_since_new_floor_down up {new_height} {ts}")

            if curr_step_floor > prev_floor and step_idx_since_new_floor_up > STEP_THRESHOLD and curr_step_floor > 0:
                floor_data = curr_step_floor - 1
                if enable_partial_completion or prev_prev_floor + 2 <= curr_step_floor or curr_step_floor <= 1:
                    this_result = 1
                logging.info(f"[{user}] Reached floor {curr_step_floor} {ts} {twitch_url} (prev_prev floor: {prev_prev_floor}) (result:{this_result})")
                step_idx_since_new_floor_up = 0
                step_idx_since_new_floor_down = 0
                prev_prev_floor = prev_floor
                prev_floor = curr_step_floor
            elif curr_step_floor < prev_floor and step_idx_since_new_floor_down > FALL_STEP_THRESHOLD:
                this_result = 0
                if prev_floor > 1:
                    logging.info(f"[{user}] Fall detected at floor {prev_floor} to floor {curr_step_floor}, ts:{ts} ({ts_jst} JST), new height {new_height}m {twitch_url} (result:{this_result})")
                if f"{prev_floor}-{curr_step_floor}" not in fall_to_floor_counter:
                    fall_to_floor_counter[f"{prev_floor}-{curr_step_floor}"] = 0
                fall_to_floor_counter[f"{prev_floor}-{curr_step_floor}"] += 1
                floor_data = prev_floor
                step_idx_since_new_floor_down = 0
                prev_prev_floor = prev_floor
                prev_floor = curr_step_floor

            if this_result >= 0:
                result["user"].append(user)
                result["day"].append(dailyData)
                result["floor"].append(floor_data)
                result["floor_result"].append(this_result)
                result["timestamp"].append(ts)
                result["on_stream"].append(on_stream)
            prev_height = new_height

def merge_data_with_local(remote_data, user):
    # '.' character not allowed in filename
    user = user.replace('.', '')

    for i in os.listdir("cache"):
        path = os.path.join("cache",i)
        if os.path.isfile(path) and user in i:
            with open(path) as f:
                local_file = json.load(f)
                for day in local_file["dailyData"]:
                    if day not in remote_data["dailyData"]:
                        remote_data["dailyData"][day] = local_file["dailyData"][day]
                        logging.info(f"Merged {day} with local cache for {user}")

    return remote_data

parse_api_data()    

df = pd.DataFrame.from_dict(result)
df.to_csv(os.path.join(RESULT_PATH, "result.csv"))
grouped = df.groupby(["user", "floor", "on_stream", "floor_result"]).size().unstack(fill_value=0)
grouped = grouped.rename(columns={0: "fail", 1:"success"})
grouped = grouped.reset_index()
grouped["helper"] = grouped["user"] + '-' + grouped['floor'].astype(str) + '-' + grouped['on_stream'].astype(str)
# Move 'helper' to the first position
full_name_col = grouped.pop('helper')
grouped.insert(0, 'helper', full_name_col)

grouped.to_csv(os.path.join(RESULT_PATH, "aggregated.csv"))

sorted_fall_to_floor_counter = {k: v for k, v in sorted(fall_to_floor_counter.items(), key=lambda item: item[1])}
for k, v in sorted_fall_to_floor_counter.items():
    logging.info(f"{k} -> {v}")




