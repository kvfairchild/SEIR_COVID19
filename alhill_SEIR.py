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


class alhillSEIRModel():

    config = dict()

    def __str__(self):
        return " | ".join([self.config["model_type"], self.config["model_name"], self.config["model_id"]])

    # This method should not need to be modified
    def get_config(self) -> dict:
        if not self.config:
            dir_path = os.path.dirname(os.path.abspath(__file__))
            with open(Path(dir_path, "config.json").as_posix()) as f:
                self.config = json.load(f)
            self.model_parameters = self.config["model_parameters"]
        return self.config

    def __init__(self):
        self.docker_run = False  # if False then use tmp for IO & model save
        self.helper = 'models/prevalence/alhill_SEIR/'
        self.tmp = 'tmp'
        self.input_dir = 'input' if self.docker_run else self.tmp
        self.output_dir = 'output' if self.docker_run else self.tmp
        self.datapath = self.tmp + '/all_rates.csv'

        with open('prevalence_utils/config.yaml') as f:
            model_params = yaml.load(f, Loader=yaml.FullLoader)
        globals().update(model_params)

        dir_path = os.path.dirname(os.path.abspath(__file__))
        common_path = os.path.join(dir_path, '..', '..', 'common')
        with open(Path(common_path, "data", "mit_zip_code_list.txt").as_posix()) as f:
            self.ZIP_CODES = f.read().splitlines()

        with open(self.input_dir + "/params.json") as f:
            params = json.load(f)
            self.t0 = params['t_0']
            self.n_samples = params['n_samples']
            self.dates = params['dates_to_simulate']
            self.t0_day = get_days_to_t0(self.t0, DAY_0) # start sampling at t_0

        os.environ['N'] = str(POPULATION)
        os.environ['INITINF'] = str(INIT_INF)
        os.environ['TINT'] = str(get_days_from_day0(DAY_0, INTERVENTION_DATE))
        os.environ['TMAX'] = str(self.t0_day + len(self.dates))

        all_df = pd.DataFrame()

        # S = susceptible
        # Inf = all infected (exposed + infected)
        # R = recovered
        # D = dead
        for run in ['S', 'Inf', 'R', 'D']:
            self.model_path = self.tmp + '/' + run + '_Intervention.csv'
            if run == 'D':
                self.d_model_path = self.model_path
            os.environ['MODELPATH'] = self.model_path
            os.environ['RUNTYPE'] = run

            subprocess.call('Rscript runIntervention.R '
                            '--Tint $TINT --Tmax $TMAX '
                            '--InitInf $INITINF --N $N '
                            '--varShow $RUNTYPE --saveModel $MODELPATH',
                            shell=True)

            df = pd.read_csv(self.model_path)
            # restrict df to t_0 and beyond
            df = df[(df['Intervention'] == 'Intervention') & (df['time'] >= self.t0_day)]
            intervention_vals = df["value"].tolist()
            intervention_rates = [val / POPULATION for val in intervention_vals]

            all_df[run] = intervention_rates

        all_df.to_csv(self.datapath, index=False)

    def zip_code_prevalence(self, dates: list, inputs_sample: dict) -> list:

        prev_vals = self.get_prevalences()

        prevalences = []
        for t_i, date in enumerate(dates):
            ma_all = {}
            ma_all['*'] = {
                "Susceptible": round(prev_vals['S'][t_i], 4),
                "Infected": round(prev_vals['Inf'][t_i], 4),
                "Recovered": round(prev_vals['R'][t_i], 4),
                "Died": round(prev_vals['D'][t_i], 4)
            }
            prevalences.append(ma_all)
            # prevalences.append({})
            # for z in self.ZIP_CODES:
            #     prevalences[-1][z] = round(prev_vals[t_i], 4)

        return prevalences

    def get_prevalences(self):

        df = pd.read_csv(self.datapath)
        df_dict = df.to_dict()

        return df_dict

    def single_draw_from_model(self, dates: list, inputs_sample: dict) -> list:
        return self.zip_code_prevalence(dates, inputs_sample)

    def sample(self, t_0: str, n_samples: int, dates: list) -> dict:
        samples = list()
        for n in range(n_samples):
            inputs_sample = dict()
            samples.append(self.single_draw_from_model(dates, inputs_sample))
        return dict(samples=samples)

    def write_output_samples_metadata(self, output_dir : str, samples : dict):
        metadata_fname = Path(output_dir, 'output_metadata.json').as_posix()
        samples_fname = Path(output_dir, 'output_samples.json').as_posix()
        print('Model storing file locally: ' + metadata_fname)
        print('Model storing file locally: ' + samples_fname)
        with open(samples_fname, 'w') as f:
            json.dump(samples, f, indent=4)
        # with open(metadata_fname, 'w') as f:
        #     json.dump(metadata, f, indent=4)

    def check_model_output(self):

        # validate model against known deaths
        check_death_predictions(self.d_model_path)


if __name__ == "__main__":

    model = alhillSEIRModel()
    samples = model.sample(model.t0, model.n_samples, model.dates)
    model.write_output_samples_metadata(model.output_dir, samples)
    model.check_model_output()