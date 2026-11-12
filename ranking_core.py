import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("college_scorecard_fully_cleaned.csv")

school_name = df['school.name']
tuition_in_state = df['latest.cost.tuition.in_state']
tutition_out_of_state = df['latest.cost.tuition.out_of_state']
state = df['latest.school.state']
median_earning_10yr = df['latest.earnings.10_yrs_after_entry.median']
median_earning_6yr = df['latest.earnings.6_yrs_after_entry.median']
admit_rate = df['latest.admissions.admission_rate.overall']
admit_rate2 = df['admit_rate_pct'] # just the prior *100
graduation_rate = df['latest.completion.completion_rate_4yr_150nt']
sat = df['latest.admissions.sat_scores.average.overall']

SCHOOL_NAME = 'school.name'
TUITION_IN_STATE = 'tuition_in_state'
TUITION_OUT_OF_STATE = 'latest.cost.tuition.out_of_state'

def create_school_metrics(index: int, is_in_state: bool = False, earning_period: str = '10yr'):
    """earning_period: '10yr', or '6yr'"""
    if is_in_state: 
        max_tuition = tuition_in_state.max()

        tuition_pct = 1 - (tuition_in_state[index] / max_tuition)
        tuition_label = tuition_in_state[index]
    else: 
        max_tuition = tutition_out_of_state.max()

        tuition_pct = 1 - (tutition_out_of_state[index] / max_tuition)
        tuition_label = tutition_out_of_state[index]

    if earning_period == '10yr':
        max_earning = median_earning_10yr.max()

        earning = median_earning_10yr[index] / max_earning
        earning_label = median_earning_10yr[index]
    elif earning_period == '6yr':
        max_earning = median_earning_6yr.max()

        earning = median_earning_6yr[index] / max_earning
        earning_label = median_earning_6yr[index]
    else: 
        print("Please select the correct string for 'earning_period'")
        earning = 0

    max_sat = sat.max()
    sat_label = sat[index]

    max_grad = graduation_rate.max()
    grad_pct_normalized = graduation_rate[index] / max_grad
    grad_label = round(graduation_rate[index] * 100, 2)

    admit_label: str = round(admit_rate[index] * 100, 2)

    # add method to set NAN/NA values to 0
    return {
        'tuition': (tuition_pct, tuition_label),
        'grad': (grad_pct_normalized, grad_label),
        'earning': (earning, earning_label),
        'admit': (admit_rate[index], admit_label), # should we do something to normalize this?
        'sat': (sat[index] / max_sat, sat_label)
    }

def create_school_profile(index: int, state_of_residecny: str, active: bool = False, earning_period: str = '10yr'):
    """
    state_of_residecny: valid 2 letter state abberivationii
    earning_period: '10yr', or '6yr'"""
    name = school_name[index]

    if state_of_residecny == state[index]:
        residency = "In-state"
        is_in_state = True
    else:
        residency = "Out-of-state"
        is_in_state = False

    metrics = create_school_metrics(index, is_in_state, earning_period)

    # TODO: create methods for
    #       1. determining feasability for attendance
    #       2. Fit score

    return {
        "name": name,
        "residency": residency,
        "metrics": metrics,
        "category": "Target",
        "fit_score": 50,
        "active": active,
    }

def generate_ranking_list(indecies: list[int], state_of_residecny: str, active: bool = False, earning_period: str = '10yr'):
    """indecies: list of indecies representing the schools in the parent csv""" 
    # active is current on or off for all, TODO: figure out how we want it to work

    return [create_school_profile(index, state_of_residecny, active, earning_period) for index in indecies]
