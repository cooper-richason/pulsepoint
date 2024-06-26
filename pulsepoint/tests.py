# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_tests.ipynb.

# %% auto 0
__all__ = []

# %% ../nbs/01_tests.ipynb 3
from .core import *
from .utils import *
import pandas as pd
from statsforecast import StatsForecast
from tqdm.autonotebook import tqdm


# %% ../nbs/01_tests.ipynb 5
def _split_dataset(df: pd.DataFrame, splt_date: str, crnt_frmt= None):
    """Split dataframe into test and training at splt_date

    If format of current column is not YYYY-mm-dd, like with GA4 api data, please specify 
    the current format (crnt_frmt)
    """
    if crnt_frmt: df['ds'] = pd.to_datetime(df['ds'],format= crnt_frmt)
    else:         df['ds'] = pd.to_datetime(df['ds'])

    splt_date = pd.to_datetime(splt_date)

    test_df = df[ df['ds']>= splt_date]
    train_df = df[ df['ds'] < splt_date]

    return train_df, test_df

# %% ../nbs/01_tests.ipynb 8
def _train_SF_model(df: pd.DataFrame,
                model: list,
                hrz: int = 7,
                freq: str = 'D',
                levels: list = [70,80,90,95,99],
                cross_validate: bool= False,
                cv_periods: int = 0,
                insample:bool = False):
    """Train Model"""

    if not isinstance(model,list): model = [model]

    sf = StatsForecast(
        df = df, 
        models = model, 
        freq = freq, 
        n_jobs = -1
        )

    fcst = sf.forecast(h = hrz, level = levels, fitted = True)
    fcst = fcst.reset_index()
    insample_forecasts = sf.forecast_fitted_values().reset_index()
    
    if cross_validate:
        crossvalidation_df = sf.cross_validation(
            df = df,
            h = hrz,
            step_size = hrz,
            n_windows = cv_periods
        )
        return fcst, cross_validate, None
    elif insample:
        insample_forecasts = sf.forecast_fitted_values().reset_index()
        return fcst, None, insample_forecasts
    else:
        return fcst, None, None

# %% ../nbs/01_tests.ipynb 11
def _evaluate_results(dataset: pd.DataFrame, fcst: pd.DataFrame,mdl_name = 'MSTL', anom_level: int = 80, levels: list = [70,80,90,95,99]):
    """ Evaluate Results to find anamalies"""

    fcst_cols = fcst.columns.difference(['unique_id','ds'])
    fcst[fcst_cols] = fcst[fcst_cols].astype(float).round(2)

    cmbd_df = pd.merge(dataset[dataset['ds'].isin(set(fcst['ds']))][['ds','y','unique_id']], fcst, on=['ds','unique_id'], how='left')
    cmbd_df = cmbd_df.sort_values(by='ds', ascending=True)

    cmbd_df['diff'] = cmbd_df['y'] - cmbd_df[mdl_name]
    cmbd_df['pct_diff'] = round(cmbd_df['diff'] / cmbd_df[mdl_name],3) * 100
    cmbd_df['anom_conf'] = 0

    # Iterate through each level of confidence to update 'anomaly_confidence'
    for level in levels:
        column_name_high = f'{mdl_name}-hi-{level}'
        column_name_low = f'{mdl_name}-lo-{level}'
    
        condition = (cmbd_df['y'] >= cmbd_df[column_name_high]) | (cmbd_df['y'] <= cmbd_df[column_name_low])
    
        cmbd_df.loc[condition, 'anom_conf'] = level

    cmbd_df = cmbd_df[['unique_id','ds','y',mdl_name,'anom_conf','diff','pct_diff']+list(cmbd_df.columns)[4:-3]]
    anoms_df = cmbd_df[cmbd_df['anom_conf'] >= anom_level]

    return cmbd_df, anoms_df
