#!/usr/bin/env python
# md5: 456873fea5b466b728ee39d3b36aee9e
#!/usr/bin/env python
# coding: utf-8



import csv
import yaml
from memoize import memoize
from copy import copy



def fix_emails_in_member_info_list(member_info_list):
  member_info_list_new = []
  for member_info in member_info_list:
    member_info = copy(member_info)
    if '@' not in member_info['email']:
      member_info['email'] = member_info['email'] + '@stanford.edu'
    member_info_list_new.append(member_info)
  return member_info_list_new

@memoize
def get_team_name_to_member_info():
  output = {}
  for team_name,member_info_list in yaml.load(open('teams.yaml', 'rt')).items():
    output[team_name] = fix_emails_in_member_info_list(member_info_list)
  return output

def get_members_on_team(team_name):
  return get_team_name_to_member_info()[team_name]

@memoize
def list_teams():
  return sorted(list(get_team_name_to_member_info().keys()))

@memoize
def get_grader_info_list():
  return fix_emails_in_member_info_list(yaml.load(open('graders.yaml', 'rt')))



def make_line_dict(header_fields, line_entries):
  output = {}
  for idx,header in enumerate(header_fields):
    entry = line_entries[idx]
    output[header] = entry
  return output

def parse_feedback(grades_file):
  is_header = True
  header_fields = None
  field_to_idx = None
  output = {}
  prev_line_dict = None
  for entries in csv.reader(open(grades_file, 'rt')):
    if is_header:
      header_fields = entries
      is_header = False
      continue
    line_dict = make_line_dict(header_fields, entries)
    if line_dict['Team Name'] == '':
      line_dict['Team Name'] = prev_line_dict['Team Name']
    team_name = line_dict['Team Name']
    grader = line_dict['Grader']
    prev_line_dict = copy(line_dict)
    blacklist = [
      'Team Name',
      'Grader',
      'Total',
      'Notes',
      '',
    ]
    subcategories = [x for x in header_fields if x not in blacklist]
    info_dict = {}
    for x in subcategories:
      info_dict[x] = line_dict[x]
    score_subcategories = []
    for x in subcategories:
      try:
        int(info_dict[x])
        score_subcategories.append(x)
      except:
        continue
    for x in score_subcategories:
      info_dict[x] = int(info_dict[x])
    total_score = sum([info_dict[x] for x in score_subcategories])
    if team_name not in output:
      output[team_name] = {
        'Team': team_name,
        'Score': total_score,
        'Comments': {}
      }
    else:
      output[team_name]['Score'] = (output[team_name]['Score'] + total_score) / 2
    if grader not in output[team_name]['Comments']:
      output[team_name]['Comments'][grader] = {}
    output[team_name]['Comments'][grader] = info_dict
  return output



# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import sendgrid
import os
from sendgrid.helpers.mail import *
from getsecret import getsecret

def send_email(recipient_info_list, cc_info_list, message_body, assignment_num, really_send=False):
  sg = sendgrid.SendGridAPIClient(getsecret('SENDGRID_API_KEY'))
  message = {}
  message['personalizations'] = [
    {
      'to': [],
      'cc': [],
      'subject': 'CS 377U Assignment Grades ' + str(assignment_num),      
    }
  ]
  for recipient_info in recipient_info_list:
    message['personalizations'][0]['to'].append({
      'email': recipient_info['email'],
      'name': recipient_info['name'],
    })
  for recipient_info in cc_info_list:
    message['personalizations'][0]['cc'].append({
      'email': recipient_info['email'],
      'name': recipient_info['name'],
    })
  message['from'] = {
    'email': getsecret('SENDER_EMAIL'),
    'name': getsecret('SENDER_NAME'),
  }
  message['content'] = [
    {
      'type': 'text/plain',
      'value': message_body,
    }
  ]
  if not really_send:
    print(message_body)
    return
  response = sg.send(message)
  print(response.status_code)
  print(response.body)
  print(response.headers)



def main():
  assignment_num = '7 Regrade'
  really_send = False
  parsed_feedback = parse_feedback(str(assignment_num) + '.csv')
  for team_name in list_teams():
    if team_name not in parsed_feedback:
      print('===== skipping team: ' + team_name + ' ======')
      continue
    feedback = parsed_feedback[team_name]
    email_body = yaml.safe_dump(feedback, default_flow_style = False, allow_unicode = True)
    send_email(get_members_on_team(team_name), get_grader_info_list(), email_body, assignment_num, really_send)



