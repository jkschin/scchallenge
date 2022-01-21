import pandas as pd
from collections import defaultdict
import pickle
import json
import plotly.graph_objects as go
import os


def build_matrices():
    df = pd.read_csv("bonus/od_matrix.csv")
    dist_dic = defaultdict(dict)
    time_dic = defaultdict(dict)
    for index, row in df.iterrows():
        source = int(row["fromlocationid"])
        dest = int(row["tolocationid"])
        dist = row["distance"]
        t = int(row["time"])
        dist_dic[source][dest] = dist
        time_dic[source][dest] = t
    with open("dist_dic.pickle", 'wb') as pfile:
        pickle.dump(dist_dic, pfile, protocol=pickle.HIGHEST_PROTOCOL)
    with open("time_dic.pickle", 'wb') as pfile:
        pickle.dump(time_dic, pfile, protocol=pickle.HIGHEST_PROTOCOL)


def read_dist_and_time_dic():
    dist_dic = pickle.load(open("dist_dic.pickle", "rb"))
    time_dic = pickle.load(open("time_dic.pickle", "rb"))
    return dist_dic, time_dic


def parse_one_json(filepath):
    data = json.load(open(filepath))
    tour = []
    try:
        trip_details = data["TripDetails"][1]
        depot_start_id = data["TripDetails"][1]["Vehicle"]["DepotStart"]["ID"]
        depot_end_id = data["TripDetails"][1]["Vehicle"]["DeptEnd"]["ID"]
        tour = [depot_start_id]
        for row in trip_details["Orders"]:
            id = row["From"]["ID"]
            tour.append(id)
        tour.append(depot_end_id)
    except:
        print("Skipped")
    return data, tour
    # return tour
    # print(trip_details["Orders"])
    # for row in trip_details:
    #     print(row)
    # print(len(trip_details))
    # print(type(trip_details))
    # print(trip_details["Vehicle"])


def draw_tour(tour):
    locations = pd.read_csv("locations.csv")
    lats = []
    longs = []
    print(tour)
    for locationid in tour:
        row = locations[locations["id"] == locationid]
        try:
            lat = float(row["locationlat"].values)
            long = float(row["locationlong"].values)
            lats.append(lat)
            longs.append(long)
        except:
            print("Skipped", locationid)
    fig = go.Figure(go.Scattermapbox(
        mode = "markers+lines",
        lon = longs,
        lat = lats,
        marker = {'size': 10}))
    print(longs, lats)

    fig.update_layout(
        margin ={'l':0,'t':0,'b':0,'r':0},
        mapbox = {
            'center': {'lon': longs[0], 'lat': lats[0]},
            'style': "stamen-terrain",})

    fig.show()
    return locations




if __name__ == "__main__":
    rootpath = "bonus/april2021/1"
    jsonfiles = os.listdir(rootpath)
    for path in jsonfiles:
        jsonpath = os.path.join(rootpath, path)
        data, tour = parse_one_json(jsonpath)
        if len(tour) != 0:
            locations = draw_tour(tour)

