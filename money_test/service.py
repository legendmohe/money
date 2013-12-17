#!/usr/bin/python
# -*- coding: utf-8 -*-
 
import btcchina
import urllib2
import json
import time

class OrderService():
	def __init__(self,access=None,secret=None):
		self.service = btcchina.BTCChina(access,secret)
		self._priceURL = "https://data.btcchina.com/data/ticker"
		
	def getCurrentPrice(self):
		try:
			req = urllib2.Request(self._priceURL)
			response = urllib2.urlopen(req)
			resp_dict = json.loads(response.read())
		except :
			print "can't get current price."
			return None
		else:
			return resp_dict["ticker"]
			
	def getAccountInfo(self):
		try:
			account = self.service.get_account_info()['result']['balance']
		except Exception as e:
			print "can't get account info. error: ", e
			return None
		else:
			return {"btc":account['btc']['amount'], "cny":account['cny']['amount']}

	def sendOrder(self, type, amount, retryTimes = 4, comfirmTimes = 3, delta = 3):
		print "start ordering. type: ", type

		price = 0.0
		ordered = False
		for i in range(0, retryTimes):
			try:
				price = self.getCurrentPrice()
				if price == None:
					time.sleep(1)  #wait for 1 second
					continue
				print str("sell %f at price:%s" %(amount, price))
				result = ""
				if(type == "buy"):
					result = self.service.buy(str(float(price['buy']) + delta), str(amount)) # +0.1 for sure
				elif(type == "sell"):
					result = self.service.sell(str(float(price['sell']) - delta), str(amount)) # -0.1 for sure
				
				print "Result : ",result
				if(result and result["result"] == True):
					ordered = True
					break
			except Exception as e:
				print "Order error: ", e
			else:
				print "Now retry sendOrder : ", i
			
			time.sleep(1)  #wait for 1 second
		
		if(ordered == False):
			print "order faild."
			return {"price":price, "result":False}
		
		orderID = "0"
		for j in range(0, comfirmTimes): 
			time.sleep(1) 
			try:
				print "checking orders... "
				for k in range(1, 5):
					time.sleep(1)
					result = self.service.get_orders()["result"]
				#print result
				if(len(result["order"]) == 0):
					return {"price":price, "result":True}
				else:
					orderID = result["order"][0]["id"]
					print "orderID: ", orderID
			except Exception as e:
				print "comfirm error : ", e
			else:
				print "Now retry get_orders : ", j
			
			time.sleep(1)  #wait for 1 second
				
				
		print "ordering faild. now cancel it. "
		
		while True: 
			try:
				for k in range(1, 2):
					time.sleep(1)
					result = self.service.get_orders()["result"]
				if(len(result["order"]) == 0):
					break
				orderID = result["order"][0]["id"]
				print "cancel orderID: ", orderID
				result = self.service.cancel(orderID)
				
				print "canceling order..."
				print "Result : ",result
				if(result and result["result"] == True):
					break
			except Exception as e:
				print "cancel error: ", e
			else:
				print "Now retry cancel : ", j
				
		return {"price":price, "result":False}

if __name__ == '__main__':
	ACCESS_KEY="bcf78b6d-83fa-4411-a330-9e386494d3ad"
	SECRET_KEY="323e18cc-0fa2-4f92-bfc8-9f044f3c424a"
	SERVICE = btcchina.BTCChina(ACCESS_KEY,SECRET_KEY)
	
	info = SERVICE.get_orders()["result"]
	
	print info
	
	# TOTAL_AMOUNT = float(info['result']['balance']['btc']['amount'])
	# amount = "0.0100"
	
	# print  amount
	# result = SERVICE.sell("9000.00", str(amount))
	# print "result: ", result
