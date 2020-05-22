# from bs4 import BeautifulSoup
import io
import os
import pandas as pd
import requests
import subprocess
import urllib
import yaml


from prevalence_utils.get_dates import get_days_to_t0, get_days_from_day0


def _set_env(model_path):

    os.environ['N'] = str(POPULATION)
    os.environ['INITINF'] = str(INIT_INF)
    os.environ['TINT'] = str(get_days_from_day0(DAY_0, INTERVENTION_DATE))
    os.environ['TMAX'] = str(365) # full year simulation
    os.environ['MODELPATH'] = model_path


# def _get_data_url():
#
#       data_dir_url = 'https://github.com/reichlab/covid19-forecast-hub/tree/master/data-processed/COVIDhub-ensemble'
#       html = urllib.request.urlopen(data_dir_url).read()
#
#       soup = BeautifulSoup(html, 'html.parser')
#
#       csvs = []
#
#       table = soup.find("table", {"class": "files"})
#       for row in table.findAll("tr"):
#             for cell in row.findAll("td", {"class": "content"}):
#                   for link in cell.findAll("a"):
#                         if link.get('title')[-3:] == 'csv':
#                               csvs.append(link.get('title'))
#
#       most_recent_datafile = csvs[-1:][0]
#
#       return most_recent_datafile
#
#
# # TODO: finish method
# # check model output against ensemble predictions at https://reichlab.io/covid19-forecast-hub/
# def _compare_to_reichlab_ensemble(df):
#
#       datafile = _get_data_url()
#
#       url = 'https://raw.githubusercontent.com/reichlab/covid19-forecast-hub/' \
#             'master/data-processed/COVIDhub-ensemble/' + datafile
#
#       s = requests.get(url).content
#       df = pd.read_csv(io.StringIO(s.decode('utf-8')))
#
#       # MA only
#       df = df[df["location_name"] == 'MA']
#       print(df)


def _get_jhu_csse():

    gba_only = False
    by_county = False

    # ground truth for deaths used by https://reichlab.io/covid19-forecast-hub/
    url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_US.csv'

    s = requests.get(url).content
    df = pd.read_csv(io.StringIO(s.decode('utf-8')))

    # MA only, drop "Out of MA" & "Unassigned"
    df = df[(df['Province_State'] == "Massachusetts")]
    df = df[(df["Admin2"] != "Out of MA") & (df["Admin2"] != "Unassigned")]

    # OPTION: select only Greater Boston Area
    if gba_only:
        county_list = ["Norfolk", "Plymouth", "Suffolk", "Essex", "Middlesex"]
        df = df[df["Admin2"].isin(county_list)]

    # make df of daily deaths
    col_list = df.keys().tolist()
    start_col = col_list.index('2/1/20') # first day of recorded cases in MA
    daily_total_df = df.iloc[:, start_col:]

    # data_date = daily_total_df.columns[-1]

    deaths = []

    # get total deaths for each day in num_days
    num_days = len(daily_total_df.keys().tolist())
    for i in range(num_days, 0, -1):
        total_deaths = sum(daily_total_df.iloc[:, -i].to_list())
        deaths.append(total_deaths)

    return deaths


# check model output against known death data from JHU
def _compare_to_jhu_csse(df):

    jhu_deaths_list = _get_jhu_csse()

    # only look at intervention data
    model_preds_list = df[(df['Intervention'] == 'Intervention')]['value'].to_list()
    model_preds_list = [int(pred) for pred in model_preds_list]

    import operator
    diff = list(map(operator.sub, model_preds_list, jhu_deaths_list))

    for i, d in enumerate(jhu_deaths_list):
        print(i, d, model_preds_list[i], diff[i])

    # visual sanity check on predicted deaths
    import matplotlib.pyplot as plt
    # plt.plot(model_preds_list[:len(jhu_deaths_list)])
    plt.plot(model_preds_list)
    plt.plot(jhu_deaths_list)
    plt.show()


def check_death_predictions(d_model_path):

    model_path = d_model_path
    df = pd.read_csv(model_path)

    _compare_to_jhu_csse(df)
    # _compare_to_reichlab_ensemble(df)

