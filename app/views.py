from django.shortcuts import render

from kiteconnect import KiteTicker
from kiteconnect import KiteConnect
from contextlib import closing 
import io
import dropbox
import math
import pandas as pd
import logging

# Create your views here.
global session_key

token = "nhbeUrgyLCwAAAAAAACzavDpQiJbs2TEdZftDj1O1q7bl7QABdb5K5BZAA932OOV" #get token on https://www.dropbox.com/developers/apps/
dbx = dropbox.Dropbox(token)
yourpath = "/NO JEE 2017/Orders.xlsx" #

api_key = "91hkrdr1b0qn8vq4"
api_secret = "boh4n0omf2yymhgojal1j7uxft1v73p8"

kite = KiteConnect(api_key=api_key)

# Relevant streamer
def stream_dropbox_file(path):
    _,res=dbx.files_download(path)
    with closing(res) as result:
        byte_data=result.content
        return io.BytesIO(byte_data)


def order(symbol, price, quantity, ttype, profit, prod_type):
    if ttype == ('BUY' or 'buy'):
        txn_type = kite.TRANSACTION_TYPE_BUY
    elif ttype == ('SELL' or 'sell'):
        txn_type = kite.TRANSACTION_TYPE_SELL

    if prod_type == ('CNC'):
        pt = kite.PRODUCT_CNC
        ex = kite.EXCHANGE_NSE
    elif prod_type == ('MIS'):
        pt = kite.PRODUCT_MIS
        ex = kite.EXCHANGE_NSE
    elif prod_type == ('NRML'):
        pt = kite.PRODUCT_NRML
        ex = kite.EXCHANGE_NFO
    
    try:
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=ex,
            tradingsymbol=symbol,
            transaction_type=txn_type,
            quantity=quantity,
            product=pt,
            order_type=kite.ORDER_TYPE_LIMIT,
            price=price,
            tag = 'ALH' + str(profit).replace('.','D')
        )
        print(str(txn_type) + " " + prod_type + " " + str(symbol) + " @ " + str(price) + " and qty = " + str(quantity) + " profit = " + str(profit) + " ID = " + order_id)
    except Exception as e:
        logging.info("Order placement failed: {}".format(e))

    return order_id


def order2(symbol, price, quantity, ttype, profit, prod_type):
    print(str(ttype) + " " + prod_type + " " + str(symbol) + " @ " + str(price) + " and qty = " + str(quantity) + " profit = " + str(profit))


def order_gen(symbol, buy_start_price, buy_order_type, buy_order_gap, buy_order_qty, number_of_buy_orders, sell_start_price, sell_order_type, sell_order_gap, sell_order_qty, number_of_sell_orders, buy_profit, sell_profit):
    # placing buy orders
    for x in range(0,int(number_of_buy_orders)):
        order(symbol = symbol, price = (float(buy_start_price) - (float(buy_order_gap) * x)), quantity = int(buy_order_qty), ttype = 'BUY', profit = str(buy_profit), prod_type = buy_order_type)
    # placing sell orders
    for x in range(0,int(number_of_sell_orders)):
        order(symbol = symbol, price = (float(sell_start_price) + (float(sell_order_gap) * x)), quantity = int(sell_order_qty), ttype = 'SELL', profit = str(sell_profit), prod_type = sell_order_type)


def get_session(request):

	if request.method == 'GET':

		session_key = request.GET.get('request_token')
		request.session['session_key'] = session_key
		file_stream=stream_dropbox_file(yourpath)
		df = pd.read_excel(file_stream, sheet_name='Sheet1')
	
		df.columns = df.iloc[1]
		x = df.iloc[2:,2:]
		

		scrips = list()

		scrip = x.to_dict('records')

		request.session['scrip'] = scrip

		for i in scrip:
			if not isinstance(i['Scrip'],float):
				scrips.append(i['Scrip'])

		return render(request,'app/index.html',{'scrips':scrips})
	


def place(request):

	if request.method == 'POST':
		
		session_key = request.session.get('session_key')
		data = kite.generate_session(session_key, api_secret=api_secret)
		kite.set_access_token(data["access_token"])

		scrip = request.session.get('scrip')
		
		file_stream=stream_dropbox_file(yourpath)
		df = pd.read_excel(file_stream, sheet_name='Sheet1')
	
		df.columns = df.iloc[1]
		x = df.iloc[2:,2:]

		for x in range(0,(len(x.index))):
			ltp = 0
			current = ''

			if scrip[x]['Buy order type'] != 'NRML':
				current = str('NSE:' + scrip[x]['Scrip'])
			else:
				current = str('NFO:' + scrip[x]['Scrip'])

			ltp = float(kite.ltp(current)[current]['last_price'])
			buying_price = min((ltp - scrip[x]['Buy Order Start Difference']),scrip[x]['Buy order price'])
			selling_price = max((ltp + scrip[x]['Sell Order Start Difference']),scrip[x]['Sell Order Price'])
			try:
				order_gen(scrip[x]['Scrip'],buying_price, scrip[x]['Buy order type'], scrip[x]['Buy Order Gap'],scrip[x]['Buy Order Quantity'], scrip[x]['Number of Buy'], selling_price, scrip[x]['Sell order type'], scrip[x]['Sell Order Gap'], scrip[x]['Sell Order Quantity'], scrip[x]['Number of Sell'], scrip[x]['Buy Profit Per Order'], scrip[x]['Sell Profit Per Order'])
			except Exception as e:
				pass

		return render(request,'app/index.html',{'scrips':scrips})

	
	