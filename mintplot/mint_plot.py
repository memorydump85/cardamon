import sys
import pandas as pd
import numpy as np
import locale
import datetime as dt
import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib import patches
from matplotlib.dates import MONDAY
from matplotlib.dates import WeekdayLocator, DateFormatter

#
# Style settings
#
plt.style.use('ggplot')
mpl.rcParams['font.family'] = 'Ubuntu'
mpl.rcParams['font.size'] = 10.0
mpl.rcParams['axes.titlesize'] = 'medium'


#
# Category group definitions
#
all_categories = {
    'Arts', 'Mobile Phone', 'Entertainment', 'Transfer', 'Fast Food',
    'Pharmacy', 'Credit Card Payment', 'Income', 'Federal Tax',
    'Uncategorized', 'Gas & Fuel', 'Rental Car & Taxi', 'Health & Fitness',
    'Home Improvement', 'Doctor', 'Utilities', 'Cash & ATM',
    'Electronics & Software', 'Paycheck', 'Furnishings', 'Gift',
    'Coffee Shops', 'Parking', 'Shipping', 'Food & Dining', 'Service & Parts',
    'Auto Payment', 'Shopping', 'Laundry', 'Investments', 'Restaurants',
    'Movies & DVDs', 'Financial', 'Mortgage & Rent', 'Business Services',
    'Hair', 'Groceries', 'Toys', 'Home', 'Clothing', 'Amusement'
}
food_categories = {
    'Fast Food', 'Coffee Shops', 'Food & Dining', 'Restaurants', 'Groceries'
}
living_categories = {
    'Home Improvement', 'Electronics & Software', 'Furnishings', 'Gift',
    'Shopping', 'Toys', 'Clothing', 'Hair'
}
entertainment_categories = {
    'Entertainment', 'Movies & DVDs', 'Amusement'
}
transport_categories = {
    'Gas & Fuel', 'Rental Car & Taxi', 'Parking', 'Auto Payment'
}


def load_csv_data(csv_file, category_filter=None):
    """
    Load csv data and adjust amounts to reflect debit/credit status
        debit => positive
        credit => negative
    """
    df = pd.read_csv(csv_file, parse_dates=[0])
    if category_filter is not None:
        df = df[df.Category.isin(category_filter)]
    df.index = range(len(df))

    # Debit transactions only
    amounts = df.Amount.values
    weights = [ 1. if v=='debit' else -1. for v in df['Transaction Type'].values ]
    adjusted = pd.Series([a*w for a, w in zip(amounts, weights)], index=df.index)
    df['Amount'] = adjusted
    return df


def main():
    csv_file = '/home/rpradeep/Downloads/transactions.csv'
    df   = load_csv_data(csv_file)
    dfg  = df[['Category', 'Description', 'Amount']]\
                .groupby('Category').sum().sort('Amount', ascending=False)
    dfD  = df[df.Amount >= 0.]
    dfgD = dfD[['Category', 'Description', 'Amount']]\
                .groupby('Category').sum().sort('Amount', ascending=False)


    locale.setlocale( locale.LC_ALL, '' )
    def strfcur(a):
        return locale.currency(a, grouping=True)

    # brewer qualitative colors
    palette = { # brewer qualitative
        'seagreen': '#1b9e77', 'pumpkin': '#d95f02',
        'blue': '#7570b3', 'pink': '#e7298a',
        'green': '#66a61e','yellow': '#e6ab02',
        'mustard': '#a6761d' }

    dates = [ dt.datetime.utcfromtimestamp(d.astype(int)*1e-9)
                for d in df.Date.values ]
    date_begin = dates[-1].strftime("%b %d")
    date_end = dates[0].strftime("%b %d")

    plt.figure(figsize=(12,6.5), facecolor='w')


    def plot_category_spending():
        # Summarize categories whose size <= $100.
        cutoff = len(dfg.Amount) if len(dfg.Amount) < 8 \
                                 else np.argmin(dfg.Amount.values >= 100.)
        category_names = dfg.index[:cutoff].tolist() + [
                            '%d Others' % (len(dfg.Amount)-cutoff) ]
        amounts = dfg.Amount[:cutoff].tolist() + [dfg.Amount[cutoff:].sum()]
        ylabels = [ c for c, a in zip(category_names, amounts) if a > 0. ]
        amounts = [ a for a in amounts if a > 0. ]
        debits = [ dfgD.Amount[c] if c in dfgD.index else 0. for c in dfg.index[:cutoff] ]

        # Setup plot style
        plt.yticks(range(len(amounts)), ylabels[::-1])
        plt.grid('off')
        plt.gca().get_xaxis().set_visible(False)
        plt.gca().patch.set_visible(False)
        plt.tick_params(axis='y', which='both', left='off', right='off')
        style = dict(height=0.6, align='center', edgecolor='0.5')
        rects = plt.barh(range(len(amounts)), debits[::-1], color=palette.values()[::-1], alpha=0.4, **style)
        rects = plt.barh(range(len(amounts)), amounts[::-1], color=palette.values()[::-1], **style)

        # Display amount to the right of each bar
        for c, a, r in zip(ylabels, amounts[::-1], rects):
            r.set_x(r.get_x()+5) # aestheics
            plt.text(r.get_width(), r.get_y()+r.get_height()/2., '  '+strfcur(a),
                va='center', size='small', color='0.4')


    def plot_timeline():
        plt.title('You spent %s between %s and %s' %
            (strfcur(df.Amount.sum()), date_begin, date_end))

        colors = [ [palette['pumpkin'], palette['seagreen']][v < 0]
                        for v in df.Amount.values ]

        # Setup plot style
        plt.gca().xaxis_date()
        plt.gca().xaxis.set_major_locator(WeekdayLocator(MONDAY))
        plt.gca().xaxis.set_major_formatter(DateFormatter("%d/%b"))
        plt.gca().autoscale_view()
        plt.gca().xaxis.grid(True, 'major')
        plt.gca().grid(True)

        staggered = [ date + dt.timedelta(hours=np.random.randint(-12, 12)) for date in dates ]
        bars = plt.bar(staggered, df.Amount.values,
                    color=colors, edgecolor='w', align='center', width=0.5, picker=1)

        def on_pick(e):
            """
            Pick handler for bar clicks.
            Display transaction summary in a separate plot on click
            """
            selected_bar = e.artist
            ix = bars.index(selected_bar)
            plt.subplot2grid((6,2),(2,1),1,1)
            _ = df.loc[ix]
            formatted = "  %s %sed on %s\n  %s\n  %s\n\
                           Category: %s\n  Account: %s" % (
                                locale.currency(_['Amount'], grouping=True ),
                                _['Transaction Type'], _['Date'], _['Description'],
                                _['Original Description'], _['Category'], _['Account Name'])
            plt.text(0, 0.5, formatted, va='center', ha='left',
                family='monospace', size='large', color='#220000')
            plt.axis('off')
            plt.gca().get_xaxis().set_visible(False)
            plt.gca().get_yaxis().set_visible(False)
            plt.gcf().canvas.draw()

        plt.gcf().canvas.mpl_connect('pick_event', on_pick)


    plt.subplot2grid((6,2),(0,0),4,1)
    plot_category_spending()
    plt.subplot2grid((6,2),(4,0),2,2)
    plot_timeline()


    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()