#!/usr/bin/python

import requests, json, re, subprocess, os, getpass
from bs4 import BeautifulSoup
from collections import OrderedDict

msg = '\nThere are new Federal Circuit cases!\n\n'
section_1 = 'Precedential\n\n'
section_2 = '\n\nNonprecedential\n\n'
trigger = False
try:
  with open('cafc_cases.json') as d:
    output = json.load(d)
except ValueError:  # In case the JSON file is empty for some reason
  output = OrderedDict()
  
url = requests.get('http://www.cafc.uscourts.gov/opinions-orders/')
soup = BeautifulSoup(url.content)
cases = soup.find_all(class_=['even','odd'])

for item in cases:
  tds = item.find_all('td')
  number = tds[1].text.strip()  # DATA: The case number
  split = re.split("[ \t]\[", tds[3].text.strip())
  name = split[0] # DATA: The case caption
  check = []  # Check if we have this decision already (each case can include multiple decisions)
  try:
    for entry in output[name]['info']:
      check.append(entry['number'])
  except KeyError:
    pass
  if number in check:
    continue
  date = tds[0].text.strip()  # DATA: The date of the decision
  link = 'http://www.cafc.uscourts.gov' + tds[3].a['href']  # DATA: The link to the PDF
  r = requests.get(link)  # Get the PDF and save it
  new_pdf = 'cafc_cases/' + name + ' ' + number + '.pdf'
  new_txt = 'cafc_cases/' + name + ' ' + number + '.txt'
  with open(new_pdf, 'wb') as fd:
    for chunk in r.iter_content(1024):
      fd.write(chunk)
  command = 'pdftotext -layout -enc UTF-8 "' + new_pdf + '" > "' + new_txt + '"' # Convert PDF to TXT for easier searching
  subprocess.call(command, shell = True)
  precedent = tds[4].text.strip() # DATA: Precedential value
  variety = split[1][0:len(split[1])-1] # DATA: What type of decision was issued
  with open(new_txt, 'r') as txt:
    contents = re.sub('\n', ' ', txt.read())
    contents = re.sub('\s+', ' ', contents)
  if variety not in ['ERRATA', 'ORDER', 'ORDER 2', 'ORDER 3', 'ORDER 4']: #DATA: The 3 judges on the panel
    judges = re.sub('(\(|\)|-\s)', '', re.search('(?<=(Before\s|CURIAM\s)).*?\.', contents).group(0))
    judges = judges.decode('utf-8')
  else:
    judges = 'Judges not stated'
  if variety != 'ERRATA': #DATA: Where the case originated
    source = re.search('(Appeal(s)?\sfrom|(On\s)?Petition\s)(.|\n)*?(?<!(\sNo|Nos|.\s.))\.', contents).group(0)
  else:
    source = 'Correction to previous Federal Circuit decision'
  data = {  # Create JSON contents
      'number': number,
      'date': date,
      'link': link,
      'precedent': precedent,
      'variety': variety,
      'source': source,
    }
  try:  # If the case exists already, add this decision as part of it
    output[name]['info'].append(data)
  except KeyError: # If the case is new, create an entry for it
    output[name] = OrderedDict()
    output[name]['info'] = []
    output[name]['info'].append(data)
  trigger = True  # Activate the email
  addition = name + ', ' + number + '\n' + source + '\nPanel: ' + judges + '\nPDF: ' + link + '\n\n'
  if precedent == 'Precedential':
    section_1 += addition
  else:
    section_2 += addition

output = json.dumps(output, indent=True, ensure_ascii=False)  # Write that file
with open('cafc_cases.json', 'w') as f:
      f.write(output)


if trigger: # Send the email
  if not os.path.exists('email_addresses.py'):
    sender = input('Enter sending GMail address: ')
    password = getpass.getpass('Enter sending address password: ')
    recipients = input('Enter recipient addresses, separated by commas: ')
  else:
    exec(compile(open('email_addresses.py').read(), 'update_anc_database_creds.py', 'exec'))
  msg = 'From: ' + sender + '\nTo: ' + recipients + '\nSubject: New Federal Circuit Cases' + msg + section_1 + section_2 # Build the email text
  msg = msg.encode('utf-8')
  import smtplib
  server = smtplib.SMTP('smtp.gmail.com:587')
  server.ehlo()
  server.starttls()
  server.login(sender, password)
  server.sendmail(sender, [recipients], msg)
