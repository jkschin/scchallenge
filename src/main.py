import pandas as pd
from meteostat import Point, Daily
from datetime import datetime
from prophet import Prophet
from prophet.diagnostics import cross_validation
from statsmodels.tools.eval_measures import rmse


def weather_augment(start, end, lat, long):
    # Create Point for Vancouver, BC
    start = datetime(start.year, start.month, start.day)
    end = datetime(end.year, end.month, end.day)
    point = Point(lat, long)

    # Get daily data for 2018
    data = Daily(point, start, end)
    data = data.fetch()
    return data

    # Plot line chart including average, minimum and maximum temperature
    # data.plot(y=['tavg', 'tmin', 'tmax', 'prcp', 'snow', 'wspd', 'tsun'])
    # plt.show()


def what_day_is_it(ds, day):
    date = pd.to_datetime(ds)
    if date.weekday() == day:
        return 1
    else:
        return 0


def is_lockdown(ds):
    date = pd.to_datetime(ds)
    lockdown = (date.year == 2021 and date.month == 12 and date.day >= 19)
    return (lockdown)


def clean_data():
    print("Reading locations and fillratehistory...")
    locations=pd.read_csv("locations.csv")
    fillratehistory=pd.read_csv("fillratehistory.csv")
    fillratehistory['aggregateid'] = 'c'+fillratehistory['containerid'].astype(str)+'_l'+fillratehistory['locationid'].astype(str)
    fillratehistory['fillratelogtime'] = pd.to_datetime(fillratehistory['fillratelogtime'])
    fillratehistory['lastemptied'] = pd.to_datetime(fillratehistory['lastemptied'])
    return fillratehistory, locations


def build_unique_container_location_df(id, fillratehistory, locations):
    print("Building unique container-location df...")
    selected_aggregateid = id
    df = fillratehistory[fillratehistory.aggregateid == selected_aggregateid].sort_values('fillratelogtime')
    df["deltas"] = df["fillratepercentage"] - df["fillratepercentage"].shift(1)
    df = df.reset_index(drop=True)
    cond1 = df[df['fillratepercentage']==0].index.tolist()
    cond2 = [i + 1 for i in cond1]
    cond3 = df[df['fillratelogtime'] == df['lastemptied']].index.tolist()
    cond4 = df[df['fillratepercentage'] + 10 <= df['fillratepercentage'].shift(-1).fillna(0)].index.tolist()
    final_indexes = set(cond1 + cond2 + cond3 + cond4)
    df = df.drop(index=final_indexes)
    df['fillratelogtime'] = df['fillratelogtime'].dt.round('H')
    df['lastemptied'] = df['lastemptied'].dt.round('H')
    df = df.drop(index=0)

    # Filtering from quantiles
    lower = df["deltas"].quantile(0.01)
    upper = df["deltas"].quantile(0.99)
    df = df[(df["deltas"] > lower) & (df["deltas"] < upper)]

    # More formatting so we can join in the weather data later.
    df["year"] = df["fillratelogtime"].dt.year
    df["month"] = df["fillratelogtime"].dt.month
    df["day"] = df["fillratelogtime"].dt.day

    # We just do some crazy thing of merging the entire locations DF first. Waste of space but this is
    # small data.
    df = pd.merge(df, locations, how='left', left_on=['locationid'], right_on=['id'])

    # There's some inefficiences here, like how there's only a single lat long.
    # Technically you don't have to merge here but I'm lazy for now. I'll fix it later
    # when stuff needs to sped up.
    lat = df["locationlat"]
    long = df["locationlong"]
    start = df["fillratelogtime"].min()
    end = df["fillratelogtime"].max()
    data = weather_augment(start.date(), end.date(), lat[0], long[0])
    data.reset_index(level=0, inplace=True)
    data["year"] = data["time"].dt.year
    data["month"] = data["time"].dt.month
    data["day"] = data["time"].dt.day
    df = pd.merge(df, data, how='left', on=['year', 'month', 'day'])

    # This rename is for prophet
    df.rename(columns={"fillratelogtime": "ds", "deltas": "y"}, inplace=True)


    # Add days data
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, value in enumerate(days):
        df[value] = df['ds'].apply(what_day_is_it, day=i)

    # Add lockdown data
    df['lockdown'] = df['ds'].apply(is_lockdown)
    df['freedom'] = ~df['ds'].apply(is_lockdown)
    return df


def build_model(df):
    print("Building model...")
    m = Prophet()
    m.add_seasonality(name='in_lockdown', period=7, fourier_order=3, condition_name='lockdown')
    m.add_seasonality(name='not_lockdown', period=7, fourier_order=3, condition_name='freedom')
    m.add_country_holidays(country_name='NL')
    m.add_regressor('tavg', mode='multiplicative')
    m.add_regressor('prcp', mode='multiplicative')
    m.add_regressor('wspd', mode='multiplicative')
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for i, value in enumerate(days):
        m.add_regressor(value, mode='multiplicative')
    m.fit(df)

    start = df["ds"].min()
    end = df["ds"].max()
    time_delimiter = end - pd.to_timedelta("7 days")

    duration = len(df["y"])
    horizon = 168
    initial = "%d hours" %(duration - horizon)
    horizon = "%d hours" %(horizon)
    df_cv = cross_validation(m, initial=initial, horizon=horizon)
    df_cv = df_cv[~df_cv["ds"].duplicated()]
    rmse_val = rmse(df_cv["yhat"], df_cv["y"])
    return rmse_val


if __name__ == "__main__":
    id = 'c11985_l8049'
    fillratehistory, locations = clean_data()
    df = build_unique_container_location_df(id, fillratehistory, locations)
    val = build_model(df)
    print(val)


# Python
import itertools
import numpy as np
import pandas as pd

num_params = 100
param_grid = {
    'changepoint_prior_scale': np.linspace(0.01, 0.5, num=num_params),
    'seasonality_prior_scale': np.linspace(0.01, 10, num=num_params),
    'holidays_prior_scale': np.linspace(0.01, 10, num=num_params),
    'seasonality_mode': ['additive, multiplicative']
}

# Generate all combinations of parameters
all_params = [dict(zip(param_grid.keys(), v)) for v in itertools.product(*param_grid.values())]
rmses = []  # Store the RMSEs for each params here

# Use cross validation to evaluate all parameters
for params in all_params:
    m = Prophet(**params).fit(df)  # Fit model with given params
    df_cv = cross_validation(m, cutoffs=cutoffs, horizon='30 days', parallel="processes")
    df_p = performance_metrics(df_cv, rolling_window=1)
    rmses.append(df_p['rmse'].values[0])

# Find the best parameters
tuning_results = pd.DataFrame(all_params)
tuning_results['rmse'] = rmses
print(tuning_results)




# def split_train_test(df):
#     time_delimiter = df["fillratelogtime"].max() - pd.to_timedelta(7, unit='days')
#     train_df = df[df["fillratelogtime"] <= time_delimiter]
#     test_df = df[df["fillratelogtime"] > time_delimiter]
#     return train_df, test_df


