#!/usr/bin/python

# Basd on the gist from
# http://www.voidynullness.net/blog/2013/07/25/gmail-email-with-python-via-imap/

import sys
import imaplib2 as imaplib
import keyring
import oauth2
import email
import simplejson as json
from bs4 import BeautifulSoup

from clientinfo import CLIENT_ID, CLIENT_SECRET



def request_access():
    import webbrowser
    
    permission_url = oauth2.GeneratePermissionUrl(CLIENT_ID)
    webbrowser.open(permission_url)

    print 'Please authorize e-mail access for app'
    print 'You will see a webpage for authorizing access'
    print 'For some reason, if the webpage does not automatically open please navigate to'
    print '    ', permission_url
    print 'in your webbrowser \n\n'

    auth_code = raw_input('Enter authorization_token from webpage: ')

    return oauth2.AuthorizeTokens(CLIENT_ID, CLIENT_SECRET, auth_code)



def authenticate_connect_imap():
    refresh_token = keyring.get_password('moneyplot', 'refresh_token')
    access_token = None

    if refresh_token is None:
        response = request_access()
        print response
        refresh_token = response[u'refresh_token']
        access_token = response[u'access_token']
        keyring.set_password('moneyplot', 'refresh_token', refresh_token)

    if access_token is None:
        response = oauth2.RefreshToken(CLIENT_ID, CLIENT_SECRET, refresh_token)
        access_token = response[u'access_token']

    auth_string = oauth2.GenerateOAuth2String('mail.pradeepr@gmail.com', access_token, False)
    imap_conn = imaplib.IMAP4_SSL('imap.gmail.com')
    imap_conn.authenticate('XOAUTH2', lambda x: auth_string)
    return imap_conn



def CHOK(v):
    retval, data = v
    if retval == 'OK': return data
    else: raise Exception('IMAP returned' + retval)



def main():
    imap = authenticate_connect_imap()
    
    CHOK( imap.select('$/umcu') )
    data = CHOK( imap.search(None, 'UnSeen') )
    for msg_num in data[0].split():
        msg_data = CHOK(imap.fetch(msg_num, '(RFC822)'))
        html = msg_data[0][1].split('\r\n\r\n')[1]

        soup = BeautifulSoup(html)
        for row in soup.select('tr')[1:]:
            cells = row.select('td')
            debit = (cells[4].text.strip()[0] == '(')

            print json.dumps([
                    -1 if debit else +1,
                    cells[1].text.strip(),
                    cells[2].text.strip(),
                    [s.encode('utf8') for s in cells[3].stripped_strings],
                    float(cells[4].text.strip().strip('$()').replace(',', ''))
                ])

    imap.close()    
    imap.logout()


if __name__ == '__main__':
    main()