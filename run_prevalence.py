# TODO: add multiple interventions option
# TODO: map to zip codes
# TODO: add D preds check against ensemble

from __future__ import division

import json
import os
import pandas as pd
from pathlib import Path
import subprocess
import yaml

from prevalence_utils.get_dates import get_days_from_day0, get_days_to_t0
from prevalence_utils.check_output import check_death_predictions


def read_input_samples_metadata(input_dir):
    with open(input_dir + "/params.json") as f:
        params = json.load(f)
    return [params['t_0'], params['n_samples'], params['dates_to_simulate']]


def set_env():

    os.environ['N'] = str(POPULATION)
    os.environ['INITINF'] = str(INIT_INF)
    os.environ['TINT'] = str(get_days_from_day0(DAY_0, INTERVENTION_DATE))
    os.environ['TMAX'] = str(t0_day + len(dates))
    os.environ['MODELPATH'] = model_path


def zip_code_prevalence(dates: list, inputs_sample: dict) -> list:

    with open("prevalence_utils/mit_zip_code_list.txt") as f:
        zip_codes = f.read().splitlines()

    prev_vals = get_prevalences()

    prevalences = []
    for t_i, date in enumerate(dates):
        prevalences.append({})
        for z in zip_codes:
            prevalences[-1][z] = round(prev_vals[t_i], 4)

    return prevalences


def get_prevalences():

    intervention_df = df[df["Intervention"] == "Intervention"]
    intervention_vals = intervention_df["value"].tolist()
    intervention_rates = [val/POPULATION for val in intervention_vals]

    return intervention_rates


def single_draw_from_model(dates: list, inputs_sample: dict) -> list:
    return zip_code_prevalence(dates, inputs_sample)


def sample(t_0: str, n_samples: int, dates: list) -> dict:
    samples = list()
    for n in range(n_samples):
        inputs_sample = dict()
        samples.append(single_draw_from_model(dates, inputs_sample))
    return dict(samples=samples)


def _get_latest_git_hash():
    hash = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
    hash_utf8 = hash.decode("utf-8")
    return str(hash_utf8[1:])


def generate_metadata(t_0:str) -> dict:
    return dict(
        model_name = 'placeholder-zip-code-prevalence-model',
        model_type = 'prevalence',
        model_id = 'V0',
        input_models=[],
        t0_date=t_0,
        model_parameters=[]
    )


def write_output_samples_metadata(output_dir : str, samples : dict, metadata : dict):
    metadata_fname = Path(output_dir, 'output_metadata.json').as_posix()
    samples_fname = Path(output_dir, 'output_samples.json').as_posix()
    print('Model storing file locally: ' + metadata_fname)
    print('Model storing file locally: ' + samples_fname)
    with open(samples_fname, 'w') as f:
        json.dump(samples, f, indent=4)
    with open(metadata_fname, 'w') as f:
        json.dump(metadata, f, indent=4)


if __name__ == "__main__":

    docker_run = False  # if False then use tmp for IO & model save
    tmp = 'tmp'
    input_dir = '/input' if docker_run else tmp
    output_dir = '/output' if docker_run else tmp
    model_path = tmp + '/CASES_Intervention.csv'

    t0, n_samples, dates = read_input_samples_metadata(input_dir)

    # load model parameters from yaml
    with open('prevalence_utils/config.yaml') as f:
        model_params = yaml.load(f, Loader=yaml.FullLoader)
    globals().update(model_params)

    t0_day = get_days_to_t0(t0, DAY_0)  # start sampling at t_0

    set_env()

    print("Running Intervention CASES model...")
    subprocess.call('Rscript runIntervention.R '
                    '--Tint $TINT --Tmax $TMAX '
                    '--InitInf $INITINF --N $N '
                    '--varShow Cases --saveModel $MODELPATH',
                    shell=True)

    df = pd.read_csv(model_path)

    # restrict df to t_0 and beyond
    df = df[(df['Intervention'] == 'Intervention') & (df['time'] >= t0_day)]

    print("Creating samples...")
    samples = sample(t0, int(n_samples), dates)

    if docker_run:
        metadata = generate_metadata(t0)
        write_output_samples_metadata(output_dir, samples, metadata)
    else:
        with open(input_dir + '/output.json', 'w') as f:
            json.dump(samples, f, indent=4)

    subprocess.call('rm $MODELPATH', shell=True)

    ## validate model against known deaths
    # check_death_predictions()