# -*- coding: utf-8 -*-
import urllib2
import json
import os
import datetime
import time
import pickle
import re
import service

import numpy as np
import sys   
reload(sys)

sys.setdefaultencoding('utf-8')  
#os.chdir(os.path.dirname(__file__))

N = 9 #天数
cK = 2.0/3.0 #k权重
cD = 2.0/3.0 #d权重
COIN_PER_BIT = 0.01
TOTAL_ACCOUNT = 100.0000
TOTAL_AMOUNT = 0.0000
CURRENT_PRICE = {}
STATUS = "prepareToSell"

BTCCHINA_DATA_URL = "http://k.btc123.com/markets/btcchina/btccny"

ACCESS_KEY="bcf78b6d-83fa-4411-a330-9e386494d3ad"
SECRET_KEY="323e18cc-0fa2-4f92-bfc8-9f044f3c424a"
SERVICE = service.OrderService(ACCESS_KEY, SECRET_KEY)

print "\n\nbegin"
print datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d-%H:%M')
print "==============================================="

def j(jsonContent):
    return json.dumps(jsonContent, indent=1)
    
def d(data, name):
    f = open(name + '.txt', 'w')
    f.write(data)
    f.close( )

def logv(data):
    f = open('log.txt', 'a')
    f.write(data)
    f.close( )
    return data

#################################################

def loadSessionID():
    global BTCCHINA_DATA_URL
    req = urllib2.Request(BTCCHINA_DATA_URL)
    response = urllib2.urlopen(req)
    sourceStr = response.read()

    target = "window.$sid = "   #正则表达式失效，不知道为什么
    nPos = sourceStr.index(target) + len(target)  + 1
    return sourceStr[nPos : nPos + 8]

SESSION_ID = loadSessionID()
def dataURL():
    global SESSION_ID
    return str("http://k.btc123.com:8080/period?step=60&sid=%s&symbol=btcchinabtccny&nonce=%d000" %(SESSION_ID, int(time.time())))

def fetchData():
    try:
        req = urllib2.Request(dataURL())
        response = urllib2.urlopen(req)
        resp_dict = json.loads(response.read())
        items = []
        for data in resp_dict:
            item = {}
            item['time'] = data[0]
            item['sell'] = data[3]*1.0
            item['buy'] = data[4]*1.0
            item['high'] = data[5]*1.0
            item['low'] = data[6]*1.0
            item['amount'] = data[7]*1.0
            items.append(item)
    except :
        return None
    else:
        return items

def loadTestData(num):
    f = open('test_data.pickle', 'rb')
    src = pickle.load(f)[-num:]
    f.close( )
    
    res = calculate(src)
    return [res[(i + 1 - 10) :i + 1] for i in range(10 - 1, len(res))]

def saveTestData(data):
    f = open('test_data.pickle', 'wb')
    pickle.dump(data, f)
    f.close( )

def saveStatus():
    global LAST_PRICE, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS
    f = open('status.pickle', 'wb')
    pickle.dump([LAST_PRICE, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS], f)
    f.close( )

def loadStatus():
    global LAST_PRICE, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS
    f = open('status.pickle', 'rb')
    data = pickle.load(f)
    f.close( )

    LAST_PRICE = data[0]
    TOTAL_ACCOUNT = data[1]
    TOTAL_AMOUNT = data[2]
    STATUS = data[3]

################################################

def calculate(items):
    global N, cK, cD
    lastK = 50.0
    lastD = 50.0
    res = [];
    chunks = [items[(i + 1 - N) :i + 1] for i in range(N - 1, len(items))]
    for chunk in chunks:
        Ln = min([item['low'] for item in chunk])
        Hn = max([item['high'] for item in chunk])
        rsv = (chunk[- 1]['sell'] - Ln)/(Hn - Ln)*100
        lastK = (N - cK)/N*lastK + cK/N*rsv
        lastD = (N - cD)/N*lastD + cD/N*lastK
        J = 3.0*lastK - 2.0*lastD

        res.append({"K":lastK, "D":lastD, "J":J, "rsv":rsv, "status":chunk[-1]})
        
    calMACD(res, 20, 30, 40)
        
    return res
    
def calMACD(items, d1, d2, d3):
    e12 = 2.0/(1 + d1)
    e26 = 2.0/(1 + d2)
    e9 = 2.0/(1 + d3)

    le12 = items[0]["status"]["sell"]    #初始值
    le26 = items[0]["status"]["sell"]
    ldif9 = e9*(le12 - le26)
    for i in range(0, len(items)):
        price = items[i]["status"]["sell"]
        le12 = e12*price + (1 - e12)*le12
        le26 = e26*price + (1 - e26)*le26
        dif = le12 - le26
        ldif9 = e9*dif + (1 - e9)*ldif9
        
        items[i]["osc"] = dif - ldif9
            

LAST_PRICE = 0.0
LAST_FLAG = "normal"
FUCKING_LINE = 0
def whatShouldDoNext(res):
    global LAST_PRICE, LAST_FLAG, FUCKING_LINE
    global STATUS
    
    OSC = [item["osc"] for item in res]

    status = res[-1]["status"]
    if(FUCKING_LINE > 0 and OSC[-1] > 0.0):
        FUCKING_LINE = 0
        return "buy"
    if(FUCKING_LINE > 0): #一次
        return "normal"
    if STATUS == 'prepareToSell' and LAST_PRICE - status["sell"] > 15:
        LAST_FLAG = "normal"
        print "stop and sell......"
        if(OSC[-1] < 0.0):
            FUCKING_LINE += 1
        return "sell"
        
    if(STATUS == 'prepareToSell' and status["sell"] - LAST_PRICE  > 50):
        return "sell"

    print("%s, %f %f %F" %(STATUS, OSC[-3], OSC[-2], OSC[-1]))

    if(STATUS == 'prepareToBuy' and all(item > 0.0 for item in OSC[-4:]) and OSC[-4] > OSC[-3] < OSC[-2] < OSC[-1]):
        LAST_FLAG = "indouble"
        return "buy"
    if(LAST_FLAG == "indouble"):
        if(OSC[-2] > OSC[-1] and status["sell"] - LAST_PRICE  > 0):
            LAST_FLAG = "normal"
            return "sell"
        else:
            return "normal"

    if  OSC[-2] < 0.0 and OSC[-2] < OSC[-1]:
        return "buy"
    elif OSC[-2] > 0.0 and  OSC[-2] > OSC[-1]: 
        return "sell"
    else:
        return "normal"

    J = [item["J"] for item in res]
    print("%f %f %F" %(J[-3], J[-2], J[-1]))
    if J[-2] < 40 and J[-1] > J[-2] : #拐上
        return "buy"
    elif J[-2] > 84 and J[-2] > J[-1]: #拐下
        return "sell"
    else:
        return "normal"

def totalMoney():
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global CURRENT_PRICE

    return TOTAL_ACCOUNT + TOTAL_AMOUNT*float(CURRENT_PRICE['sell'])

##################################################

def buyIt():
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global COIN_PER_BIT
    global CURRENT_PRICE
    global LAST_PRICE
    global SERVICE
    
    result = SERVICE.sendOrder("buy", COIN_PER_BIT)
    if(result["result"] == False):
        return False

    CURRENT_PRICE = result["price"]
    LAST_PRICE = float(CURRENT_PRICE['buy'])

    info = SERVICE.getAccountInfo()
    TOTAL_ACCOUNT = float(info["cny"])
    TOTAL_AMOUNT = float(info["btc"])

    log = "buy it at " + datetime.datetime.fromtimestamp(time.time()).strftime('%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    buy price: %f  |  current-amount: %f, current-account: %f\n" %(float(CURRENT_PRICE["buy"]), TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def sellIt():
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global COIN_PER_BIT
    global CURRENT_PRICE
    global SERVICE
    
    # amount = TOTAL_AMOUNT - 0.001
    amount = COIN_PER_BIT
    result = SERVICE.sendOrder("sell", COIN_PER_BIT)
    
    if(result["result"] == False):
        return False

    CURRENT_PRICE = result["price"]

    info = SERVICE.getAccountInfo()
    TOTAL_ACCOUNT = float(info["cny"])
    TOTAL_AMOUNT = float(info["btc"])
    
    log = "sell it at " + datetime.datetime.fromtimestamp(time.time()).strftime('%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    earn: %f" %((float(CURRENT_PRICE["sell"]) - LAST_PRICE - 6)*amount));
    log += str("    sell price: %f  |  current-amount: %f, current-account: %f\n" %(float(CURRENT_PRICE["sell"]), TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def testBuyIt(buy, time):
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global COIN_PER_BIT
    global CURRENT_PRICE
    global LAST_PRICE

    CURRENT_PRICE = {"sell":buy}
    LAST_PRICE = float(buy)
    TOTAL_ACCOUNT -= COIN_PER_BIT*float(buy)
    TOTAL_AMOUNT += COIN_PER_BIT

    log = "buy it at " + datetime.datetime.fromtimestamp(time).strftime('%m/%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    buy price: %f  |  current-amount: %f, current-account: %f\n\n" %(buy, TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def testSellIt(sell, time):
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global COIN_PER_BIT
    global CURRENT_PRICE

    CURRENT_PRICE = {"sell":sell}
    TOTAL_ACCOUNT += COIN_PER_BIT*float(sell)
    TOTAL_AMOUNT -= COIN_PER_BIT

    log = "sell it at " + datetime.datetime.fromtimestamp(time).strftime('%m/%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    sell price: %f  |  current-amount: %f, current-account: %f\n\n" %(sell, TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

################################################

def main():
    global STATUS, CURRENT_PRICE
    while True:
        print "current: ", 
        items = fetchData()
        if items == None:
            print "error fetch data. " 
            continue
        res = calculate(items[-200:])
        command = whatShouldDoNext(res)
        if command == "buy":
            if STATUS == "prepareToBuy" and buyIt(): 
                STATUS = "prepareToSell"
        elif command == "sell":
            if STATUS == "prepareToSell" and sellIt():
                STATUS = "prepareToBuy"
        #buyIt()
        saveStatus()
        time.sleep(5)

def test():
    global STATUS, CURRENT_PRICE
    datas = loadTestData(200)
    T = []
    J = []
    DD = []
    K = []
    S = []
    A = []
    MACD = []
    for data in datas:
        #print j(data)
        status = data[-1]['status'] 
        time = status['time']
        buy = (status['buy'] + status['sell'])/2.0
        sell = (status['sell'] + status['buy'])/2.0

        T.append(datetime.datetime.fromtimestamp(time).strftime('%d-%H:%M'))
        J.append(data[-1]['J'])
        DD.append(data[-1]['D'])
        K.append(data[-1]['K'])
        S.append(status['sell'])
        A.append(status['amount'])
        MACD.append(data[-1]['osc'])

        command = whatShouldDoNext(data)
        if command == "buy":
            if STATUS != "prepareToSell" and testBuyIt(buy, time): 
                STATUS = "prepareToSell"
        elif command == "sell":
            if STATUS != "prepareToBuy" and testSellIt(sell, time):
                STATUS = "prepareToBuy"

    KDJ = "\n".join([str("%s,%f,%f,%f,%f,%f,%f" %(t, k, di, j, s, a, m)) for (k, di, j, t, s, a, m) in zip(K, DD, J, T, S, A,MACD)])
    d(KDJ, "test_data")

####################  main  #####################
#loadStatus()
info = SERVICE.getAccountInfo()
print STATUS, info
TOTAL_ACCOUNT = float(info["cny"])
TOTAL_AMOUNT = float(info["btc"])
#saveStatus()


main()

#################### testing #####################
#saveTestData(fetchData())  
#test()

