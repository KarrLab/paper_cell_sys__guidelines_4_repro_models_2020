""" Estimate relative influence of tools and standards in Ten best practices for making reproducible biochemical models

:Author: Arthur Goldberg <Arthur.Goldberg@mssm.edu>
:Date: 2020-04-21
:Copyright: 2020, Karr Lab
:License: MIT
"""
import datetime
from pprint import pprint
from openpyxl import load_workbook
from serpapi.google_scholar_search_results import GoogleScholarSearchResults
import ast
import bibtexparser
import csv
import re
import requests
import sys
import time
import xml.etree.ElementTree as ET
import urllib.parse

BIBLIOGRAPHY = 'paper_cell_sys__guidelines_4_repro_models_2020.bib'
CURATED_STANDARDS_FILE = 'curated_standards.xlsx'
OUTPUT_LATEX_TABLE_FILE = 'curated_standards.tex'
PUB_MED_TEMPLATE = 'https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/{}/citedby/?tool=pubmed'
TOOL_EMAIL = 'tool=mssm_citation_research&email=Arthur.Goldberg%40mssm.edu'
EUTILS = 'eutils.ncbi.nlm.nih.gov/entrez/eutils'
NCBI_ELINK_TEMPLATE = (f"https://{EUTILS}/elink.fcgi?dbfrom=pubmed&linkname=pubmed_pmc_ref"
                       f"s&id={{}}&{TOOL_EMAIL}")
NCBI_ESEARCH_TEMPLATE = f"https://{EUTILS}/esearch.fcgi?db=pubmed&term={{}}"
ID_CONVERTER_API = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?&ids={{}}&{TOOL_EMAIL}"
ESUMMARY_TEMPLATE = f"https://{EUTILS}/esummary.fcgi?db=pubmed&id={{}}&retmode=json&{TOOL_EMAIL}"
CITATION_COUNT_RE = "Is Cited by the Following (\d+) Articles"
PUB_YEAR_RE = '<span class="citation-publication-date">(\d+)'
SLEEP_TIME = 0.4


class GoogleScholar(object):

    SERP_API_KEY = '8973042c37e0867a7cf0bddfdfb7dae2ee16268f5a331f5d5149c9a370a939e0'

    @staticmethod
    def get_gs_results(title):
        return '', 20, 2010, []

    @staticmethod
    def get_gs_results_real(title):
        # get num citations, publication year, and title from GS
        errors = []
        pub_year = None
        client = GoogleScholarSearchResults({"q": title, "serp_api_key": GoogleScholar.SERP_API_KEY})
        data = client.get_json()
        summary = data['organic_results'][0]['publication_info']['summary']
        PUB_YEAR_RE = '(\d\d\d\d)'
        match = re.search(PUB_YEAR_RE, summary)
        if match is None:
            errors.append(f"cannot get year for {title}")
        else:
            pub_year = int(match.group(1)) 
        num_citations = data['organic_results'][0]["inline_links"]["cited_by"]["total"]
        gs_title = data['organic_results'][0]["title"]
        return gs_title, num_citations, pub_year, errors


class NCBIUtils(object):

    @staticmethod
    def get_pm_id(title):
        """ Get PubMed ID for a title from the PutMed service, if possible """
        url = NCBI_ESEARCH_TEMPLATE.format(urllib.parse.quote(title))
        errors = []
        time.sleep(SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"NCBI_ESEARCH_TEMPLATE request error {response.status_code} for title '{title}'")
            return None, errors
        root = ET.fromstring(response.text)
        pm_ids = [int(id.text) for id in root.iter('Id')]
        if len(pm_ids) == 0:
            return None, None
        if len(pm_ids) == 1:
            return pm_ids[0], None
        elif 1 < len(pm_ids):
            for pm_id in pm_ids:
                _, pm_title, errors = NCBIUtils.get_pub_metadata(pm_id)
                if errors:
                    return None, errors
                # ignore case in match
                if pm_title.casefold() == title.casefold():
                    return pm_id, None
            return None, None

    @staticmethod
    def get_num_citations(pm_id):
        url = NCBI_ELINK_TEMPLATE.format(pm_id)
        errors = []
        time.sleep(SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"request error {response.status_code} for pmc_id {pmc_id}")
            return None, errors
        return NCBIUtils.get_num_citations_from_xml(response.text), None

    @staticmethod
    def get_num_citations_from_xml(xml_string):
        root = ET.fromstring(xml_string)
        num_citations = len(list(root.iter('Id'))) - 1
        return num_citations

    @staticmethod
    def get_pub_metadata(pm_id):
        # get publication year
        url = ESUMMARY_TEMPLATE.format(pm_id)
        errors = []
        time.sleep(SLEEP_TIME)
        response = requests.get(url)
        if response.status_code != requests.codes.ok:
            errors.append(f"request error {response.status_code} for pm_id {pm_id}")
            return (None, errors)
        resp_dict = dict(ast.literal_eval(response.text))
        pubdate = resp_dict["result"][str(pm_id)]["pubdate"]
        PUB_YEAR_RE = "(\d+)"
        match = re.search(PUB_YEAR_RE, pubdate)
        if match is None:
            errors.append(f"year not found in '{pubdate}' for {pm_id}")
        else:
            pub_year = int(match.group(1)) 
        # get title
        title = resp_dict["result"][str(pm_id)]["title"][:-1]
        return pub_year, title, errors

class Biblio(object):
    def __init__(self, filename):
        self.filename = filename
        with open(filename) as bibtex_file:
            self.bib_database = bibtexparser.load(bibtex_file)

    def get_entry_key(self, title):
        """ Get the bibliography key for a title """
        for citation in self.bib_database.entries:
            if citation['title'] == title:
                return citation['ID']

class CuratedStandards(object):

    # curated standard keys
    STANDARD = 'Standard / tool'
    TYPE = 'Type'
    TITLE = 'Title'
    BIB_KEY = 'bib_key'
    PUB_YEAR = 'pub_year'
    PM_ID = 'PM_id'
    PM_CITATIONS = 'PM_citations'
    GS_CITATIONS = 'GS_citations'

    def __init__(self, filename, biblio):
        self.filename = filename
        self.biblio = biblio
        self.curated_standards = self.read_curated_standards(filename)

    def read_curated_standards(self, filename):
        workbook = load_workbook(filename, data_only=True)
        curated_standards_ws = workbook.active
        field_names = [col_name_cell.value for col_name_cell in curated_standards_ws[1]]
        records = []
        for row in curated_standards_ws.iter_rows(min_row=2):
            new_record = {}
            for field_name, cell in zip(field_names, row):
                new_record[field_name] = cell.value
            records.append(new_record)
        return records

    def check_all_titles(self):
        titles = self.read_curated_standards_column(self.TITLE)
        missing = set()
        for title in titles:
            if not self.biblio.get_entry_key(title):
                missing.add(title)
        if missing:
            print('Missing titles:', missing, file=sys.stderr)
        else:
            print(f"All {len(titles)} title(s) found.")

    def read_curated_standards_column(self, col_name):
        entries = []
        for curated_standard in self.curated_standards:
            if col_name in curated_standard:
                entries.append(curated_standard[col_name])
        return entries

    def enrich_with_pm_ids(self):
        missing_ids = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            pm_id, errors = NCBIUtils.get_pm_id(curated_standard[self.TITLE])
            if pm_id is not None:
                curated_standard[self.PM_ID] = pm_id
            elif errors is None:
                missing_ids.append((title, 'no error'))
            else:
                missing_ids.append((title, errors))            
        if missing_ids:
            print('Titles missing PM citations:', file=sys.stderr)
            pprint(missing_ids, stream=sys.stderr)
        else:
            print('All references have PM ids.')

    def enrich_with_num_pm_citations(self):
        missing_pm_cites = []
        for curated_standard in self.curated_standards:
            if self.PM_ID in curated_standard:
                pm_id = curated_standard[self.PM_ID]
                num_citations, errors = NCBIUtils.get_num_citations(pm_id)
                if num_citations is not None:
                    curated_standard[self.PM_CITATIONS] = num_citations
                else:
                    title = curated_standard[self.TITLE]
                    missing_pm_cites.append(title)
        if missing_pm_cites:
            print('Titles missing PM citations:', file=sys.stderr)
            pprint(missing_pm_cites, file=sys.stderr)
        else:
            print('All references with PM ids have PM citations.')

    def enrich_with_bib_key(self):
        missing_bib_keys = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            entry_key = self.biblio.get_entry_key(title)
            if entry_key is not None:
                curated_standard[self.BIB_KEY] = entry_key
            else:
                missing_bib_keys.append(title)
        if missing_bib_keys:
            print('Titles missing bib key:', file=sys.stderr)
            pprint(missing_bib_keys, stream=sys.stderr)
        else:
            print('All references have bibliography keys.')

    def enrich_with_gs_data(self):
        missing_gs_data = []
        for curated_standard in self.curated_standards:
            title = curated_standard[self.TITLE]
            gs_title, num_citations, pub_date, errors = GoogleScholar.get_gs_results(title)
            if num_citations is None or pub_date is None or errors:
                missing_gs_data.append((title, errors))
            else:
                curated_standard[self.GS_CITATIONS] = num_citations
                curated_standard[self.PUB_YEAR] = pub_date
        if missing_gs_data:
            print('Titles not found on Google Scholar:', file=sys.stderr)
            pprint(missing_gs_data, stream=sys.stderr)
        else:
            print('All references found on Google Scholar.')

    @staticmethod
    def year_fraction(date):
        # from https://stackoverflow.com/a/36949905
        start = datetime.date(date.year, 1, 1).toordinal()
        year_length = datetime.date(date.year+1, 1, 1).toordinal() - start
        return date.year + float(date.toordinal() - start) / year_length

    @staticmethod
    def drop_columns(row, cols_to_drop):
        new_row = []
        for entry, drop in zip(row, cols_to_drop):
            if not drop:
                new_row.append(entry)
        return new_row
        
    def generate_latex_table(self, columns_to_drop=None):
        # columns: standard, type, title with reference, year published, PM citations / year, GS citations / year
        # columns_to_drop contains true values for columns to remove from the table
        columns = (self.STANDARD,
                   self.TYPE,
                   'Citation',
                   'Pub. year',
                   'PubMed cites / yr.',
                   'Scholar cites / yr.')
        column_alignments = ('l',
                             'l',
                             'l',
                             'c',
                             'c',
                             'c')
        column_alignments = ('m{2.2cm}',
                             'm{5cm}',
                             'm{1.2cm}',
                             'm{1cm}',
                             'm{1.2cm}',
                             'm{1cm}')
        small_columns = (1,
                         1,
                         0,
                         1,
                         1,
                         1)
        n_columns = len(columns)
        current_year = self.year_fraction(datetime.datetime.today())
        rows = []
        for curated_standard in self.curated_standards:

            row = [''] * n_columns
            row[0] = curated_standard[self.STANDARD]
            row[1] = curated_standard[self.TYPE]
            # row[2] = f"\\tiny{{{curated_standard[self.TITLE]}}}\cite{{{curated_standard[self.BIB_KEY]}}}"
            row[2] = f"\cite{{{curated_standard[self.BIB_KEY]}}}"

            if self.PUB_YEAR in curated_standard:
                row[3] = str(curated_standard[self.PUB_YEAR])
                age = current_year - curated_standard[self.PUB_YEAR]
                if age <= 0:
                    print(f"age ({age}) of '{curated_standard[self.TITLE]}' <= 0", file=sys.stderr)
                    continue

                # compute PM citations / year
                if self.PM_CITATIONS in curated_standard:
                
                    PM_cites_per_year = curated_standard[self.PM_CITATIONS] / age
                    row[4] = f"{PM_cites_per_year:.1f}"

                # compute GS citations / year
                if self.GS_CITATIONS in curated_standard:
                
                    GS_cites_per_year = curated_standard[self.GS_CITATIONS] / age
                    row[5] = f"{GS_cites_per_year:.1f}"

            sized_row = []
            for shrink, entry in zip(small_columns, row):
                if shrink:
                    entry = f"\\small{{{entry}}}"
                sized_row.append(entry)
            rows.append(sized_row)

        for row in rows:
            print(row)

        END_OF_LINE = '\\\\\n'
        HLINE = '\\hline\n'
        TABLE_START = '\n\\begin{tabular}'
        TABLE_END = '\\end{tabular}\n'
        table = [TABLE_START]
        if columns_to_drop:
            column_alignments = drop_columns(column_alignments, columns_to_drop)
        table.append('{ |' + '|'.join(column_alignments) + '| } \n')
        table.append(HLINE)
        if columns_to_drop:
            columns = drop_columns(columns, columns_to_drop)
        small_columns = [f"\\scriptsize{{{col}}}" for col in columns]
        table.append(' &'.join([f"\\textbf{{{col}}}" for col in small_columns]))
        table.append('\\\\ \n')
        table.append(HLINE)
        for row in rows:
            if columns_to_drop:
                row = drop_columns(row, columns_to_drop)
            table.append(' &'.join(row))
            table.append(END_OF_LINE)
            table.append(HLINE)
        table.append(TABLE_END)
        complete_table = ''.join(table)
        # todo: 
        # fit on 1 page, or multipage it
        # sort by decreaseing Schollar cites
        # make citations work
        # include in paper
        # commit
        # get feedback
        print(complete_table)
        return complete_table

    def output_latex_table(self, filename=OUTPUT_LATEX_TABLE_FILE, columns_to_drop=None):
        with open(filename, 'w') as latex_table:
            latex_table.write(self.generate_latex_table(columns_to_drop=columns_to_drop))


def main():
    biblio = Biblio(BIBLIOGRAPHY)
    curated_standards = CuratedStandards(CURATED_STANDARDS_FILE, biblio)
    curated_standards.check_all_titles()
    curated_standards.enrich_with_gs_data()
    curated_standards.enrich_with_pm_ids()
    curated_standards.enrich_with_bib_key()
    curated_standards.enrich_with_num_pm_citations()
    print('curated_standards')
    pprint(curated_standards.curated_standards)
    # curated_standards.output_latex_table(columns_to_drop=(False, False, True, False, False, False))
    curated_standards.output_latex_table()

if __name__ == '__main__':
    main()













def main_old(pmids):
    print(f"PM ID\t# PM cites\t# GS cites\tyear\ttitle")
    errors = []
    for pmid in pmids:
        num_citations, error = get_num_citations(pmid)
        if error is not None:
            errors.extend(error)

        year, title, error = get_pub_metadata(pmid)
        if error is not None:
            errors.extend(error)

        gs_title, num_gs_citations = get_gs_results(title)
        
        print(f"{pmid}\t{num_citations}\t{num_gs_citations}\t{year}\t{title}")

    if errors:
        print('Errors:')
        print('\n'.join(errors))

def get_num_citations_old(pm_id):
    url = NCBI_ELINK_TEMPLATE.format(pm_id)
    errors = []
    # time.sleep(SLEEP_TIME)
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        errors.append(f"request error {response.status_code} for {pm_id}")
        return (0, None, errors)

    citations = 0
    match = re.search(CITATION_COUNT_RE, response.text, flags=re.ASCII)
    if match is None:
        errors.append(f"no citations count for {pm_id}")
    else:
        citations = int(match.group(1)) 

    year = None
    match = re.search(PUB_YEAR_RE, response.text, flags=re.ASCII)
    if match is None:
        errors.append(f"no year for {pm_id}")
    else:
        year = int(match.group(1)) 

    return (citations, year, errors)

def get_pmc_id_old(pm_id):
    # convert PM ID to PMC ID
    url = ID_CONVERTER_API.format(pm_id)
    errors = []
    time.sleep(SLEEP_TIME)
    response = requests.get(url)
    if response.status_code != requests.codes.ok:
        errors.append(f"request error {response.status_code} for pm_id {pm_id}")
        return (None, errors)
    root = ET.fromstring(response.text)
    record = list(root.iter('record'))[0]
    # {'requested-id': '23193287', 'pmcid': 'PMC3531190', 'pmid': '23193287', 'doi': '10.1093/nar/gks1195'}
    return record.attrib['pmcid'], None
