#!/usr/bin/python

import requests, sys, json, re, subprocess, os, getpass, smtplib
# import ghostscript
from bs4 import BeautifulSoup
from collections import OrderedDict

# mkdir -p in python, from:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise

# ensure cafc_cases dir exists
mkdir_p("cafc_cases")

msg = '\nNo new cases.\n\n'
section_1 = 'Precedential\n\n'
section_2 = '\n\nNonprecedential\n\n'
trigger = False
try:
  with open('cafc_cases.json') as d:
    output = json.load(d)
except ValueError:  # In case the JSON file is empty for some reason
  output = OrderedDict()

start = 'http://www.cafc.uscourts.gov/opinions-orders/'
if '-w' in sys.argv:
  start = 'http://www.cafc.uscourts.gov/opinions-orders/7/all'
elif '-m' in sys.argv:
  start = 'http://www.cafc.uscourts.gov/opinions-orders/30/all'
elif '-y' in sys.argv:
  start = 'http://www.cafc.uscourts.gov/opinions-orders/365/all'
urls = [start]
for url in urls:
  url = requests.get(url)
  soup = BeautifulSoup(url.content)
  if soup.find('a', title='Next'):
    urls.append('http://www.cafc.uscourts.gov' + soup.find('a', title='Next')['href'])

def pdf_read(new_pdf, new_txt):
    with open(new_pdf, 'wb') as fd:
      for chunk in r.iter_content(1024):
        fd.write(chunk)
    subprocess.call('pdftotext -layout -enc UTF-8 "' + new_pdf + '" > "' + new_txt + '"', shell = True) # Convert PDF to TXT for easier searching
    precedent = tds[4].text.strip()  # DATA: Precedential value
    variety = re.search('(?<=\[).*(?=\])', tds[3].text.strip()).group(0)  # DATA: What type of decision was issued
    with open(new_txt, 'r') as txt:
      contents = re.sub('\t+', ' ', txt.read())
#    if len(contents) < 10:  # Perform emergency OCR, if necessary
#      txt.close()
#      subprocess.call('touch "' + new_tiff + '"', shell=True)
#      subprocess.call(['gs', '-sDEVICE=tiffg4', '-dNOPAUSE', '-r600x600', '-sOutputFile="./' + new_tiff + '"', '"./' + new_pdf +'"'])
#      ghostscript.Ghostscript('quit')
#      subprocess.call('tesseract "' + new_tiff + '" "' + file_stem + '"', shell=True)
#      with open (new_txt, 'r') as txt:
#        contents = re.sub('\t+', ' ', txt.read())
    try:
      ruling = re.sub('\s+', ' ', re.search('(AFFIRMED|REVERSED|REMANDED|VACATED|DISMISSED)(.|\n)*?(?=(\.|$|(?<=ED)\n))', contents).group(0))
      ruling = ruling.title()
    except AttributeError:
      ruling = 'Unmarked ' + variety.lower() + '. Check the PDF.'
    try:
      judges = re.sub('(\(|\)|-\s)', '', re.search('(?<=(Before\s|CURIAM\s|Curiam\s))(.|\n)*?(?=\.)', contents).group(0))
    except AttributeError:
      try:
        judges = re.search('PER\sCURIAM', contents).group(0)
      except AttributeError:
        judges = 'Judges not stated'
    judges = re.sub('\s+', ' ', judges).title()
    judges = judges.decode('utf-8')
    if variety.find('ERRATA') > -1:  # DATA: Where the case originated
      source = 'Correction to previous Federal Circuit decision'
    else:
      source = re.sub('\n', ' ', re.search('(On\sappeal|Appeal(s)?\sfrom|(On\s)?Petition[^er])(.|\n)*?(?<!(\sNo|Nos|.\s.))\.', contents).group(0))
      source = source.title()
    data = {  # Create JSON contents
        'number': number,
        'date': date,
        'link': link,
        'precedent': precedent,
        'variety': variety,
        'source': source,
        'judges': judges,
        'ruling': ruling,
      }
    return data

for url in urls:
  soup = BeautifulSoup(requests.get(url).content)
  cases = soup.find_all(class_=['even','odd'])
  for item in cases:
    tds = item.find_all('td')
    number = tds[1].text.strip()  # DATA: The case number
    name = re.search('^.*?(?=\s\[)', tds[3].text.strip()).group(0)  # DATA: The case caption
    name = re.sub('/', ' ', name)  # Take out slashes, which otherwise mess up file structure
    date = tds[0].text.strip()  # DATA: The date of the decision
    check = []  # Check if we have this decision already (each case can include multiple decisions)
    try:
      for entry in output[name]['info']:
        check.append(entry['number'] + entry['date'])
    except KeyError:
      pass
    if number + date in check:
      continue
    print name, number
    link = 'http://www.cafc.uscourts.gov' + tds[3].a['href']  # DATA: The link to the PDF
    r = requests.get(link)  # Get the PDF and save it
    file_stem = 'cafc_cases/' + name + ' ' + number
    new_pdf = file_stem + '.pdf'
    new_txt = file_stem + '.txt'
    new_tiff = file_stem + '.tiff'
    data = pdf_read(new_pdf, new_txt)
    print data
    try:  # If the case exists already, add this decision as part of it
      output[name]['info'].append(data)
    except KeyError: # If the case is new, create an entry for it
      output[name] = OrderedDict()
      output[name]['info'] = []
      output[name]['info'].append(data)
    trigger = True  # Turn the email positive
    msg = '\nThere are new Federal Circuit cases!\n\n'
    addition = name + ', ' + number + '\nRuling: ' + data['ruling'] + '\n' + data['source'] + '\nPanel: ' + data['judges'] + '\nPDF: ' + link + '\n\n'
    if data['precedent'] == 'Precedential':
      section_1 += addition
    else:
      section_2 += addition

output = json.dumps(output, indent=True, ensure_ascii=False)  # Write that file
#with open('cafc_cases.json', 'w') as f:
#      f.write(output)

# Send the email if there are new cases
if not os.path.exists('email_addresses.py'):
  sender = input('Enter sending GMail address: ')
  password = getpass.getpass('Enter sending address password: ')
  recipients = input('Enter recipient addresses, separated by commas: ')
else:
  exec(compile(open('email_addresses.py').read(), 'update_anc_database_creds.py', 'exec'))
if len(section_1) < 25:
  section_1 += 'None\n\n'
if len(section_2) < 25:
  section_2 += 'None'
if trigger:
  msg = msg + section_1 + section_2
msg = 'From: ' + sender + '\nTo: ' + ', '.join(recipients) + '\nSubject: Federal Circuit Report' + msg # Build the email text
msg = msg.encode('utf-8')
print msg
server = smtplib.SMTP('smtp.gmail.com:587')
server.ehlo()
server.starttls()
server.login(sender, password)
#server.sendmail(sender, recipients, msg)
