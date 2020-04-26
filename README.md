# Data and code for Veronica Porubsky, et al., *Ten best practices for making reproducible biochemical models*, Cell Systems, 2020

This Git repository contains data and code used in the paper Veronica Porubsky, Arthur Goldberg, Anand Rampadarath, David Nickerson, Jonathan Karr, and Herbert Sauro, Ten best practices for making reproducible biochemical models, Cell Systems, 2020.

[//]: # (Todo: add exact paper reference; check table number and name.)
[//]: # (Todo: add exact paper reference.)


## Overview
This Git repository contains code and data that were used to create Table 2, Standards and tools ordered by estimated influence.
The table can be reproduced by following the instructions below.

## Prerequisites

Running this software requires the following prerequisites:

1. Python 3
2. Git
3. An account to the Google Search API with provided by [SerpApi](https://serpapi.com/). As of April, 2020, [free developer trials](https://serpapi.com/#pricing) are available. The 5,000 searches allowed by a trial will be amply sufficient to run this software.

## Instructions

Clone this repository. At the command line, enter:

    git clone https://github.com/KarrLab/paper_2018_curr_opin_sys_biol.git

Create a file named `keys.py`.
Copy the API key provided by [SerpApi](https://serpapi.com/manage-api-key) into the value of `SERP_API_KEY` in the `keys.py` file.

Run this script to reproduce the table's data:

    reproduce_table_2.sh

The table will be reproduced in two formats.
A LaTeX version is provided in `evaluated_standards.tex`.
A `tsv` version is provided in `evaluated_standards.tsv`.

## Questions or feedback

Contact [mailto](mailto:Arthur dot Goldberg@mssm.edu).
