# Copyright (C) 2021 Frederick W. Nielsen
#
# This file is part of surveymonkey-things.
#
# flowroute-things is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# flowroute-things is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with flowroute-things.  If not, see <http://www.gnu.org/licenses/>.

"""
Bulk builds new surveys in SurveyMonkey based on a built-template
"""

import csv
import os
from time import sleep

import requests
import yaml

# specifies separate config file containing non-portable parameters
# looks for a YAML file in the user's home directory under the subfolder "Personal-Local"
# i.e. c:\users\jsmith\Personal-Local\config.yml
CONFIG_FILE = os.path.join(os.path.expanduser('~'), "Personal-Local", "config.yml")

STAT_WAIT = ', please wait...'
STAT_LIST = f'Looking for survey templates{STAT_WAIT}\n'
STAT_BUILD = 'Building new survey: '

INPUT_SEARCH = 'Specify template survey name (partial okay): '
INPUT_CHOICE = '\nPlease confirm survey to copy from: '

CSV_INPUT_FILE = './survey_bulk_adder.csv'

# CSV column headers
TITLE = 'Session Title'
PRESENTER = 'Presented By'
VANITY_URL = 'Survey URL'

COLLECTOR_OPTS = {
    'type': 'weblink',
    'thank_you_message': 'Thank you for voting!\n- Your Tech Team',
    'disqualification_url': 'http://www.somecompany.com/',
    'redirect_url': 'http://www.somecompany.com/',
    'redirect_type': 'url'
}

COLLECTOR_URL_OPTS = {'type': 'weblink',
    'domain': 'www.surveymonkey.com',
    'domain_type': 'surveymonkey'
}


ERR_API_AUTH = 'API call unauthorized:\n'
ERR_API_OTHER = 'API call encountered error:\n'
ERR_NO_RESULTS = 'No surveys found, check query string or menu selection.'
ERR_MANY_RESULTS = 'Too many surveys returned, raise max results in script or use better query'

# maximum number of surveys to return in search result
PER_PAGE = 10

SM_API_URL = 'https://api.surveymonkey.com/v3/surveys'

SM_PRIAPI_LINK_URL = 'https://www.surveymonkey.com/collect/update_link'
SM_PRIAPI_COLL_URL = 'https://www.surveymonkey.com/collect/update_collector_options'
SM_META_TEXT = "Please take this survey about the Company 2021 session you recently attended."
SM_META_THUMBNAIL = "https://www.yourserver.com/thumbnail.png"


def exit_error(error_string):
    """print error message and exit"""
    print(error_string)
    raise SystemExit

def sm_api_call(api_obj, method = False, payload='', suffix=''):
    """throw something at api"""
    api = api_obj[1]
    url = api_obj[0] + suffix

    success = False
    while success is False:
        # check the http method
        if not method:
            sm_request = api.get(url, params=payload)
        elif method == 'post':
            sm_request = api.post(url, json=payload)
        elif method == 'patch':
            sm_request = api.patch(url, json=payload)
        elif method == 'xxx':
            sm_request = api.post(url, data=payload)

        if sm_request.status_code == 200 or sm_request.status_code == 201:
            success = True
        elif sm_request.status_code == 429:
            print ('server busy, retrying...')
            sleep(.5)
            continue
        else:
            exit_error(
                f'{ERR_API_OTHER}{sm_request.status_code}: {sm_request.content.decode("utf-8")}'
                )

        return sm_request.json()

def main():
    """most everything is done here"""

    # grab non-portable parameters from external config file
    with open(CONFIG_FILE, 'r') as config_file:
        config_params = yaml.full_load(config_file)

    # need own surveymonkey API token - RTFM
    sm_config = config_params['surveymonkey']
    # next 2 are used for the private API and is most easily scraped from a browser session
    sm_cookie = sm_config['admin_ui_cookie']
    sm_referer = sm_config['admin_ui_referer']
    sm_headers = {
        'Authorization': f'Bearer {sm_config["auth_token"]}',
        'Cookie': sm_cookie,
        'referer': sm_referer
        }


    # read session list from csv
    with open(CSV_INPUT_FILE, encoding='ansi') as file:
        csv_file = csv.DictReader(file)
        new_survey_list = [row for row in csv_file]

    # # query user for search string
    search_for = input(INPUT_SEARCH)

    # init web handler
    sm_api_client = requests.Session()
    sm_api_client.headers.update(sm_headers)
    sm_api_obj = [SM_API_URL, sm_api_client]
    sm_pri_api_url_obj = [SM_PRIAPI_LINK_URL, sm_api_client]
    sm_pri_api_meta_obj = [SM_PRIAPI_COLL_URL, sm_api_client]

    # get survey list
    print(STAT_LIST)
    sm_search = sm_api_call(sm_api_obj, payload={'title': search_for, 'per_page': PER_PAGE})

    # we get a good number of results?
    if sm_search['total'] == 0:
        exit_error(ERR_NO_RESULTS)
    elif sm_search['total'] > PER_PAGE:
        exit_error(ERR_MANY_RESULTS)


    # menu to confirm survey template
    counter = 1
    for survey in sm_search['data']:
        print(f'{counter}: {survey["title"]}')
        counter += 1

    # ask user to confirm
    try:
        template_num = int(input(INPUT_CHOICE))
    except ValueError:
        exit_error(ERR_NO_RESULTS)

    if template_num >= 0 and template_num < sm_search['total']+1:
        template_num -= 1
    else:
        exit_error(ERR_NO_RESULTS)

    # survey id to copy from
    sm_template_id = sm_search['data'][template_num]['id']

    total = len(new_survey_list)
    count = 1

    built_surveys = list()

    for survey in new_survey_list:
        title = survey[TITLE].strip()
        presenter = survey[PRESENTER].strip()
        vanity_url = survey[VANITY_URL].strip()

        print(f'{STAT_BUILD}#{count} of {total} - {title} ({vanity_url}){STAT_WAIT}')

        new_survey_json = {'title': title, 'from_survey_id': sm_template_id}

        # # create new survey copy
        sm_survey = sm_api_call(sm_api_obj, method = 'post', payload = new_survey_json)

        # get survey page ID (current implementation only tweaks the first page)
        sm_pages = sm_api_call(sm_api_obj, suffix = f'/{sm_survey["id"]}/pages')
        sm_first_page = sm_pages['data'][0]

        # modify description of page to presenter from csv data
        sm_api_call(sm_api_obj, method = 'patch',
            payload = {'description': f'{PRESENTER} - {presenter}'},
            suffix = f'/{sm_survey["id"]}/pages/{sm_first_page["id"]}')

        # create a new collector for the survey
        sm_collector = sm_api_call(sm_api_obj, method='post',
            payload = dict(COLLECTOR_OPTS, **{'name': vanity_url}),
            suffix = f'/{sm_survey["id"]}/collectors')

        # set custom URL for collector, script heads off private undocumented API territory now
        sm_url_payload = dict({'collector_id': sm_collector['id'],
                               'slug': f'{vanity_url}'},
                               **COLLECTOR_URL_OPTS)
        sm_api_call(sm_pri_api_url_obj, method = 'xxx',
            payload = sm_url_payload)

        # set custom link metadata, more private API hijinx here
        sm_metadata_payload = {"collector_id":int(sm_collector['id']),
                               "custom_meta_info":
                               {"title": title,
                                "description": SM_META_TEXT,
                                "image_url": SM_META_THUMBNAIL}
                                }

        sm_api_call(sm_pri_api_meta_obj, method = 'post',
            payload=sm_metadata_payload)

        built_surveys.append({'title': title,
                              'presenter': presenter,
                              'slug': vanity_url,
                              'id': sm_survey['id']
                             })
        count += 1

    # output results
    output_keys = built_surveys[0].keys()
    with open(f'{CSV_INPUT_FILE}output.csv', 'w', newline='')  as output_file:
        csv_writer = csv.DictWriter(output_file, output_keys)
        csv_writer.writeheader()
        csv_writer.writerows(built_surveys)

if __name__ == "__main__":
    main()
