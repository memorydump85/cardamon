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
import jsonpickle
import os.path
import re


#-------------------------------------- 
class WebPageUtil(object):
#--------------------------------------
    def __init__(self):
        self.twillbuf = StringIO()
        twill.set_output(self.twillbuf)


    def pageinfo(self):
        self.twillbuf.seek(0)
        twillc.info()

        info = {}
        for line in self.twillbuf.getvalue().split('\n'):
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
            print status
            traceback.print_stack()
            sys.exit(-1)


#--------------------------------------
class UMCUWeb(object):
#--------------------------------------
    def __init__(self):        
        self.pgutil = WebPageUtil()
        self.username = ''
        self.password = ''

    def login(self):
        twillc.go('https://www.umcu.org/')
        twillc.fv('4', 'UsernameField', self.username)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Password')
        twillc.fv('1', 'PasswordField', self.password)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/MainAccounts/List')
        print '[%s] LOGIN SUCCESSFUL' % str(datetime.datetime.now())


    def login_interactive(self):
        print '''
I will ask you for you UMCU login information. I will take
care not to record this information anywhere.

Remember that UMCU freezes weblogins after three
unsuccessful attempts. If I fail to log you in, please go
to https://www.umcu.org/ and verify your login information

Lets begin now ...

'''
        twillc.go('https://www.umcu.org/')
        self.username = raw_input('UMCU UserName: ')
        twillc.fv('4', 'UsernameField', self.username)
        twillc.submit('SubmitNext')

        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Password')
        self.password = getpass.getpass('UMCU Password: ')
        twillc.fv('1', 'PasswordField', self.password)
        twillc.submit('SubmitNext')

        print 'UMCU wants you to answer a security question:\n'
        self.pgutil.ensure_url('https://my.umcu.org/User/AccessSignin/Challenge')
        soup = BeautifulSoup(twillc.show())
        print soup.select('#AccessForm td')[2].text
        twillc.fv('1', 'Answer', raw_input('Security Challenge Answer: '))
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
        holds.reverse()
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


    def merge(self, holds):
        if (holds is None) or (len(holds)==0):
            return None

        K = len(holds)
        print '  %d holds found' % K

        # merge new hold with existing. compare tail of existing list
        # with head of new hold list. the old and new lists might overlap
        # so find the truly new holds.
        for k in range(K+1):
            R = K-k
            if self.holds[-R:] == holds[:R]:
                self.holds.extend(holds[R:])
                self.holds = self.holds[-100:]  # max 100 entries

                with open('holds.json', 'w') as jsonfile:
                    jsonfile.write(jsonpickle.encode(self.holds))

                print '  New holds:', holds[R:]
                return holds[R:]


#--------------------------------------
class GMailAccount(object):
#--------------------------------------
    def __init__(self):
        self.username = ''
        self.password = ''


    def login_interactive(self):
        print '''\
I will need your GMail credentials to send mails to you.
I will not record this information anywhere.

'''        
        self.username = raw_input('GMail UserName: ')
        self.password = getpass.getpass('GMail password: ')

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
        posted = umcu.get_posted_holds()
        new_holds = hist.merge(posted)

        if new_holds is not None:
            for hold in new_holds:
                print '  Notifying: ' + hold
                info = hold.split('|')
                subject = '%s: %s' % (info[-1], info[2])

                msg = '''%s on %s for account %s''' % (info[0], info[3], info[1])
                msg += '\n\n(notification by cardamon)'
                gmail.send_email([gmail.username], '[$] '+subject, msg)
        
        time.sleep(2*60) # Refresh every 2 mins


if __name__ == '__main__':
    main()