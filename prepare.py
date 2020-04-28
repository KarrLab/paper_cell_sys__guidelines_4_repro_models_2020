#!/usr/bin/env python
""" Prepare to estimate relative influence of tools and standards

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2020-04-28
:Copyright: 2020, Karr Lab
:License: MIT
"""
import subprocess


def prepare():
    """ Prepare to create the table: install Python packages; get the survey data; check the keys module
    """
    cmd = 'pip install -r requirements.txt'
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE)
    if ('Successfully built' not in str(result.stdout) and
        'Requirement already satisfied' not in str(result.stdout)):
        raise ValueError(f"Error: '{cmd}' failed")

    cmd = 'git clone https://github.com/KarrLab/paper_2018_curr_opin_sys_biol.git'
    result = subprocess.run(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if "Cloning into 'paper_2018_curr_opin_sys_biol'" not in str(result.stderr):
        raise ValueError(f"Error: '{cmd}' failed; paper_2018_curr_opin_sys_biol/ may need to be removed")

    # test that keys.py exists and contains SERP_API_KEY
    msg = "Error: SERP_API_KEY variable must be defined in keys.py"
    try:
        import keys
        if not hasattr(keys, 'SERP_API_KEY'):
            raise ValueError(msg)
    except Exception:
        raise ValueError(msg)
    print('Prepare successful.')


if __name__ == '__main__':
    prepare()
