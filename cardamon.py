#!/usr/bin/python

import twill
import twill.commands as twillc
import string
import sys, traceback
import getpass
import time, datetime
import smtplib
from bs4 import BeautifulSoup
from StringIO import StringIO


twillbuf = StringIO()


def pageinfo():
#-------------------------------------- 
    info = {}
    global twillbuf

    twillbuf.seek(0)
    twillc.info()

    for line in twillbuf.getvalue().split('\n'):
        if len(line.strip()) > 0:
            parts = line.strip().split(': ')
            if len(parts) > 1:
                info[parts[0].strip()] = string.join(parts[1:], ': ')
            else:
                info[parts[0].strip()] = ''

    return info


def ensure_url(url, status=None):
#-------------------------------------- 
    if status is None:
        status = pageinfo()

    if (status['URL'] != url or status['HTTP code'] != '200'):
        print status
        traceback.print_stack()
        sys.exit(0)


def umcu_login():
#-------------------------------------- 
    print '''
I will ask you for you UMCU login information. I will take
care not to record this information anywhere.

Remember that UMCU freezes weblogins after three
unsuccessful attempts. If I fail to log you in, please go
to https://www.umcu.org/ and verify your login information

Lets begin now ...

'''
    twillc.go('https://www.umcu.org/')
    twillc.fv('4', 'UsernameField', raw_input('UMCU UserName: '))
    twillc.submit('SubmitNext')

    ensure_url('https://my.umcu.org/User/AccessSignin/Password')
    twillc.fv('1', 'PasswordField', getpass.getpass('UMCU Password: '))
    twillc.submit('SubmitNext')

    print 'UMCU wants you to answer a security question:\n'
    ensure_url('https://my.umcu.org/User/AccessSignin/Challenge')
    soup = BeautifulSoup(twillc.show())
    print soup.select('#AccessForm td')[2].text
    twillc.fv('1', 'Answer', raw_input('Security Challenge Answer: '))
    twillc.submit('SubmitNext')

    ensure_url('https://my.umcu.org/User/MainAccounts/List')
    print '\nLOGIN SUCCESSFUL\n\n'


def send_email(sender, to_list, subject, text, gmail_user, gmail_pwd):
#--------------------------------------
    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (sender, ", ".join(to_list), subject, text)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(sender, to_list, message)
        server.close()
        print "  Email notification sent"
    except:
        print "  Email notification failed! Verify credentials and restart this program"


def get_last_posted_hold():
#--------------------------------------
    twillc.reload()
    soup = BeautifulSoup(twillc.show())
    holds_info = [row.text for row in soup.select('#HoldsId table tr.BasicLine')]

    last_hold = []
    for e in holds_info[0].split('\r'):
        if len(e.strip()) > 0:
            last_hold.append(e.strip())
    
    return last_hold


def relative_day(date):
#--------------------------------------
    delta = datetime.datetime.today() - date
    if delta.days == 0:
        return 'today'
    else if delta.days == 1:
        return 'yesterday'
    else
        return ('%d days ago' % delta.days)


def main():
#--------------------------------------
    twill.set_output(twillbuf)
    umcu_login()
    
    print '''\
I will also need your GMail credentials to send mails to
you. I will not record this information anywhere.

'''
    guser = raw_input('GMail username: ')
    gpasswd = getpass.getpass('GMail password: ')

    if not guser.endswith('@gmail.com'):
        guser = guser + '@gmail.com'

    print '\nThanks!\nBegin monitoring holds ...'
    print 'Notifications will be sent to ' + guser + '\n\n'

    # Navigate to the account informations page
    twillc.go('https://my.umcu.org/User/MainAccounts/List')

    # Start monitoring holds
    last_hold = ''
    while True:
        info = get_last_posted_hold()
        hold = '%s: %s' % ([info[-1], info[2]])
        print hold

        if hold != last_hold:
            msg = '''Posted on %s for account %s''' % (info[3], info[1])
            send_email(guser, [guser], '[$] '+ hold, msg, guser, gpasswd)

        last_hold = hold
        time.sleep(180)


if __name__ == '__main__':
    main()