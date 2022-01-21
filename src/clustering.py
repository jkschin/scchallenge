from k_means_constrained import KMeansConstrained
import plotly.graph_objects as go
import pandas as pd
import colorsys
from collections import defaultdict


def cluster(df, n_clusters, size_min, size_max):
    """
    :param df: A Pandas DataFrame with latitude and longitude only.
    :param n_clusters: Number of centroids.
    :param size_min: Minimum size of cluster.
    :param size_max: Maximum size of cluster.
    :return: (centroids, labels)
    """
    # print("cluster bounds: ({}, {})".format(size_min, size_max))
    # KM = KMeansConstrained(df, n_clusters, (size_min, size_max))
    # KM.init_seeds()
    # KM.cluster()
    # return KM.centroid, KM.label
    kmeans = KMeansConstrained(n_clusters, size_min, size_max)
    kmeans.fit(df)
    return kmeans.cluster_centers_, kmeans.labels_


def plot(dic, wcode):
    N = len(dic.keys())
    HSV_tuples = [(x*1.0/N, 0.5, 0.5) for x in range(N)]
    RGB_tuples = list(map(lambda x: colorsys.hsv_to_rgb(*x), HSV_tuples))
    print(RGB_tuples)
    mapbox_access_token = "pk.eyJ1IjoiamtzY2hpbiIsImEiOiJja3lramlqc3IxZDQ0Mm9vbGJ1ZW1yZmJxIn0.O4g4wrTYiobrQ7kN_zgifQ"

    fig = go.Figure()
    sizes = [len(v["locationlat"]) for k, v in dic.items()]
    smallest = min(sizes)
    largest = max(sizes)
    for k, v in dic.items():
        site_lat = v["locationlat"]
        site_lon = v["locationlong"]
        locations_name = v["locationname"]
        fig.add_trace(go.Scattermapbox(
            lat=site_lat,
            lon=site_lon,
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=10,
                color="rgb%s" %str(RGB_tuples[k]),
                opacity=0.7
            ),
            text=locations_name,
            hoverinfo='text'
        ))

    wcode_map = {
        200201: "Residual Waste",
        200202: "Organic Waste",
        200203: "PMD Waste",
        200204: "Glass Waste",
        200205: "200205 (Unknown)",
        200206: "Textile Waste",
        200208: "Mixed Waste"
    }
    fig.update_layout(
        title="Waste Code: %s | Smallest Cluster: %d | Largest Cluster %d | Total Clusters: %d | Total Containers: %d" %(wcode_map[int(wcode)], smallest, largest, N, sum(sizes)),
        autosize=True,
        hovermode='closest',
        showlegend=False,
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=dict(
                lat=52.0116,
                lon=4.3571
            ),
            pitch=0,
            zoom=12,
            style='light'
        ),
    )

    fig.show()


if __name__ == "__main__":
    df = pd.read_csv("container_location_wastetype.csv")
    wastetypecodes = list(df["wastetypecode"].unique())
    for wcode in wastetypecodes:
        df2 = df[df["wastetypecode"] == wcode].reset_index()
        total = len(df2)
        size_min = 30
        size_max = 50
        n_clusters = total // 40
        centers, labels = cluster(df2[["locationlat", "locationlong"]], n_clusters, size_min, size_max)
        df2["labels"] = pd.Series(labels).values
        dic = defaultdict(lambda: defaultdict(list))
        for i, label in enumerate(labels):
            lat = df2.iloc[i]["locationlat"]
            long = df2.iloc[i]["locationlong"]
            name = df2.iloc[i]["locationname"]
            dic[label]["locationlat"].append(lat)
            dic[label]["locationlong"].append(long)
            dic[label]["locationname"].append(name)
        plot(dic, wcode)
        df2.to_csv("clusters/%s_clusters.csv" %wcode)
