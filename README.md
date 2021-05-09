# surveymonkey-things

Scriptlets used to help automate survey creation and result reporting. Makes use of [SurveyMonkey's public API](https://developer.surveymonkey.com/api/v3/) as well as private API calls to get some advanced things done.

*Note that SurveyMonkey restricts API calls to 500 per day, so some of these limits may apply with your use-case.*

## [survey_bulk_adder.py](survey_bulk_adder.py)
Using a source survey as a template, imports additional surveys in bulk from CSV and sets 