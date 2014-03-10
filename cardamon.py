#!/usr/bin/python

import twill
import twill.commands as twillc
from bs4 import BeautifulSoup
from cStringIO import StringIO
import string
import re
import sys
import os.path
import time
import datetime
import smtplib
import getpass
import jsonpickle
import keyring
from collections import Counter


#--------------------------------------
class SecureStorage(object):
#--------------------------------------
    forget_stored = False

    @staticmethod
    def get(objname, hidden_input=True):
        value = keyring.get_password('cardamon', objname)
        if value is None or SecureStorage.forget_stored:
            if hidden_input:
                value = getpass.getpass(objname + ': ')
            else:
                value = raw_input(objname + ': ')
            keyring.set_password('cardamon', objname, value)
        else:
            print '%s: [using stored info]' % objname
        
        return value


#--------------------------------------
class WebPageUtil(object):
#--------------------------------------
    def __init__(self):
        #ignore twill output, until we need it
        twill.set_output(StringIO())

    def pageinfo(self):
        buf = StringIO()
        twill.set_output(buf)
        twillc.info()

        info = {}
        for line in buf.getvalue().split('\n'):
            if len(line.strip()) > 0:
                parts = line.strip().split(': ')
                if len(parts) > 1:
                    info[parts[0].strip()] = string.join(parts[1:], ': ')
                else:
                    info[parts[0].strip()] = ''

        return info


    def ensure_url(self, url, status=None):
        if status is None:
            status = self.pageinfo()

        if (status['URL'] != url or status['HTTP code'] != '200'):
            status['URL0'] = url
            raise Exception(str(status))


#--------------------------------------
class UMCUWeb(object):
#--------------------------------------
    def __init__(self):        
        self.pgutil = WebPageUtil()
        self.username = ''
        self.password = ''

    def login(self):
        twillc.go('https://www.umcu.org/')
        self.pgutil.ensure_url('https://www.umcu.org/')
        twillc.fv('4', 'UsernameField', self.username)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Password')
        twillc.fv('1', 'PasswordField', self.password)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/MainAccounts/List')
        print '[%s] LOGIN SUCCESSFUL' % str(datetime.datetime.now())


    def login_interactive(self):
        print '''
Cardamon will need your UMCU and GMail login information.
The UMCU login information will be used to automatically
login into the UMCU web-portal and monitor your holds.
The GMail login information will be used to send e-mails
when new holds are posted to your account. All login
information will be stored SECURELY.

To re-enter login information start cardamon with the
--from-scratch flag:
  ./cardamon.py --from-scratch

Remember that UMCU freezes weblogins after three
unsuccessful attempts. If login fails for any reason, please
go to https://www.umcu.org/ and verify your login
information

Lets begin now ...

'''
        twillc.go('https://www.umcu.org/')
        self.username = SecureStorage.get('UMCU UserName', False)
        twillc.fv('4', 'UsernameField', self.username)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Password')
        self.password = SecureStorage.get('UMCU Password')
        twillc.fv('1', 'PasswordField', self.password)
        twillc.submit('SubmitNext')

        print 'UMCU wants you to answer a security question:'
        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Challenge')
        soup = BeautifulSoup(twillc.show())
        question = soup.select('#AccessForm td')[2].text.strip() + '\n'
        twillc.fv('1', 'Answer', SecureStorage.get(question, False))
        twillc.fv('1', 'Remember', 'True')        
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/MainAccounts/List')
        print '\nLOGIN SUCCESSFUL\n\n'


    def get_posted_holds(self):
        print '[%s] Checking holds ...' % str(datetime.datetime.now())
        twillc.go('https://my.umcu.org/User/MainAccounts/List')
        self.pgutil.ensure_url('https://my.umcu.org/User/MainAccounts/List')
        soup = BeautifulSoup(twillc.show())
        
        holds = [ re.sub('\s{2,}', '|', row.text.strip())
                    for row in soup.select('#HoldsId table tr.BasicLine')]
        return holds


#--------------------------------------
class CardHoldHistory(object):
#--------------------------------------
    def __init__(self):
        if os.path.isfile('holds.json'):
            with open('holds.json') as jsonfile:
                self.holds = jsonpickle.decode(jsonfile.read())
        else:
            self.holds = []


    def merge(self, posted):
        if (posted is None) or (len(posted)==0):
            return []

        old_set = set(self.holds)
        new_holds = list(set(posted) - old_set)

        if len(new_holds) > 0:
            self.holds.extend(new_holds)
            self.holds = self.holds[-1000:]   # max 1000 entries

            with open('holds.json', 'w') as jsonfile:
                jsonfile.write(jsonpickle.encode(self.holds))

        print '  %d holds found. %d new holds' % (len(posted), len(new_holds))
        return new_holds


#--------------------------------------
class GMailAccount(object):
#--------------------------------------
    def __init__(self):
        self.username = ''
        self.password = ''


    def login_interactive(self):
        self.username = SecureStorage.get('GMail UserName', False)
        self.password = SecureStorage.get('GMail password')

        if not self.username.endswith('@gmail.com'):
            self.username = self.username + '@gmail.com'

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.quit()
            print 'GMail login information verified'
        except:
            print 'GMail login failed!', sys.exc_info()
            sys.exit(-1)


    def send_email(self, to_list, subject, text):
        message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (self.username, ", ".join(to_list), subject, text)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587) #or port 465 doesn't seem to work!
            server.ehlo()
            server.starttls()
            server.login(self.username, self.password)
            server.sendmail(self.username, to_list, message)
            server.close()
            print "  Email notification sent"
        except:
            print "  Email notification failed!", sys.exc_info()


def main():
#--------------------------------------
    umcu = UMCUWeb()
    umcu.login_interactive()

    gmail = GMailAccount()
    gmail.login_interactive()

    hist = CardHoldHistory()
    
    print '\nBegin monitoring holds ...'
    print 'Notifications will be sent to ' + gmail.username + '\n\n'

    # def relative_day(date):
    #     delta = datetime.datetime.today() - date
    #     if delta.days == 0:
    #         return 'today'
    #     else if delta.days == 1:
    #         return 'yesterday'
    #     else
    #         return ('%d days ago' % delta.days)


    # Start monitoring holds
    while True:
        umcu.login()
 
        try:
            posted = umcu.get_posted_holds()
        except Exception, e:
            print (e, '\n\nPausing holds monitoring because of exception\n',
                      'Will resume in 60 mins')
            gmail.send_email([gmail.username], 'Holds monitoring paused' +
                'An exception was encountered. Holds monitoring will be paused for 60 mins\n' +
                '(notification by cardamon)')
            time.sleep(60*60)
            continue

        # Are there duplicate posts?
        duplicates = [k for k, v in Counter(posted).items() if v > 1]
        if len(duplicates) > 0:
            msg = 'The following holds may have been posted multiple times to your account:\n'
            for hold in duplicates:
                msg += '    ' + '  '.join(hold.split('|')) + '\n'
            msg += '(notification by cardamon)'
            gmail.send_email([gmail.username], 'Duplicate Holds', msg)

        new_holds = hist.merge(posted)

        if len(new_holds) > 0:
            for hold in new_holds:
                print '  Notifying: ' + hold
                info = hold.split('|')
                subject = '%s: %s' % (info[-1], info[2])

                msg = '''%s on %s for account %s''' % (info[0], info[3], info[1])
                msg += '\n(notification by cardamon)'
                gmail.send_email([gmail.username], subject, msg)
        
        time.sleep(15*60) # Refresh every 15 mins


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--from-scratch':
        SecureStorage.forget_stored = True

    main()