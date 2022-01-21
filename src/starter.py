import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
import statsmodels.api
from datetime import datetime
import matplotlib.pyplot as plt
from meteostat import Point, Daily


def read_df():
    locations=pd.read_csv("locations.csv")
    fillratehistory=pd.read_csv("fillratehistory.csv")
    fillratehistory['aggregateid'] = 'c'+fillratehistory['containerid'].astype(str)+'_l'+fillratehistory['locationid'].astype(str)
    fillratehistory['fillratelogtime'] = pd.to_datetime(fillratehistory['fillratelogtime'])
    fillratehistory['lastemptied'] = pd.to_datetime(fillratehistory['lastemptied'])
    return fillratehistory


def get_one_container_location_pair(fillratehistory, selected_aggregateid):
    rate_history_selection = fillratehistory[fillratehistory.aggregateid == selected_aggregateid].sort_values('fillratelogtime')
    start_date = rate_history_selection['fillratelogtime'].iloc[0]
    rate_history_selection['hours_passed'] = [round(((x - start_date).total_seconds())/3600) for x in
                                              rate_history_selection['fillratelogtime']]
    for hour in range(len(rate_history_selection)-2, -1, -1):
        if rate_history_selection['hours_passed'].iloc[hour] == rate_history_selection['hours_passed'].iloc[hour+1]:
            if abs(((rate_history_selection['fillratelogtime'].iloc[hour] - start_date).total_seconds())/3600 - rate_history_selection['hours_passed'].iloc[hour]) > abs(((rate_history_selection['fillratelogtime'].iloc[hour + 1] - start_date).total_seconds())/3600 - rate_history_selection['hours_passed'].iloc[hour + 1]):
                rate_history_selection.drop(rate_history_selection.iloc[hour+1].name, inplace=True)
                rate_history_selection.drop(rate_history_selection.iloc[hour].name, inplace=True)
            else:
                if hour+2 != len(rate_history_selection):
                    rate_history_selection.drop(rate_history_selection.iloc[hour+2].name, inplace=True)
                rate_history_selection.drop(rate_history_selection.iloc[hour+1].name, inplace=True)
    rate_history_selection['fill_percentage_increase'] = np.nan
    for hour in range(1, len(rate_history_selection)):
        if rate_history_selection['hours_passed'].iloc[hour - 1] == rate_history_selection['hours_passed'].iloc[hour] - 1:
            rate_history_selection['fill_percentage_increase'].iloc[hour] = rate_history_selection['fillratepercentage'].iloc[hour] - rate_history_selection['fillratepercentage'].iloc[hour - 1]
    rate_history_selection = rate_history_selection[rate_history_selection['fillratelogtime'] != rate_history_selection['lastemptied']]
    delete = []
    for hour in range(len(rate_history_selection)-1):
        if rate_history_selection['hours_passed'].iloc[hour + 1] >= rate_history_selection['hours_passed'].iloc[hour] + 10:
            delete.append(hour)

    for hour in range(len(rate_history_selection)-2, -1, -1):
        if hour in delete:
            rate_history_selection.drop(rate_history_selection.iloc[hour].name, inplace=True)
    rate_history_selection.drop(rate_history_selection.iloc[0].name, inplace=True)
    rate_history_selection.hours_passed = rate_history_selection.hours_passed - rate_history_selection.hours_passed.iloc[0]
    starttime = rate_history_selection.fillratelogtime.iloc[0]
    starttime = starttime.replace(second=0, microsecond=0, minute=0, hour=starttime.hour)+timedelta(hours=starttime.minute//30)
    endtime = starttime + timedelta(hours=max(rate_history_selection.hours_passed))
    date_range = pd.date_range(start=starttime, end=endtime, periods=(endtime-starttime).total_seconds()/3600+1).to_frame().drop(columns=0)
    date_range['rate_history_selection'] = np.nan
    for i, hour in enumerate(rate_history_selection.hours_passed):
        date_range['rate_history_selection'].iloc[hour] = rate_history_selection.fill_percentage_increase.iloc[i]
    return date_range


def weather_augment():
    start = datetime(2018, 1, 1)
    end = datetime(2018, 12, 31)

    # Create Point for Vancouver, BC
    vancouver = Point(51.99006256, 4.348576874)

    # Get daily data for 2018
    data = Daily(vancouver, start, end)
    data = data.fetch()

    # Plot line chart including average, minimum and maximum temperature
    data.plot(y=['tavg', 'tmin', 'tmax', 'prcp', 'snow', 'wspd', 'tsun'])
    plt.show()


if __name__ == "__main__":
    fillratehistory = read_df()
    selected_aggregateid = 'c11985_l8049'
    df = get_one_container_location_pair(fillratehistory, selected_aggregateid)
