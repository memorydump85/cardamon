import cgi
import cgitb


def main():
    cgitb.enable()
    print "Content-Type: text/json"
    print

    print '['
    with open('transactions.jsonl') as f:
        for line in f:
            print '%s,' % line.rstrip()
    print ']'


if __name__ == '__main__':
    main()
