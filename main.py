 # -*- coding: utf-8 -*-
import urllib2
import json
import os
import datetime
import time
import pickle
import numpy as np
import Stats

#os.chdir(os.path.dirname(__file__))

N = 9 #天数
cK = 2.0/3.0 #k权重
cD = 2.0/3.0 #d权重
EACH_BIT = 1.0000
TOTAL_ACCOUNT = 10000.0000
TOTAL_AMOUNT = 0.0000
CURRENT_PRICE = {}
STATUS = "selling"

CURRENT_PRICE_URL = "https://data.btcchina.com/data/ticker"

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

def dataURL():
    return "http://k.btc123.com:8080/period?step=300&sid=ff4447e4&symbol=btcchinabtccny&nonce=" + str(int(time.time())) + "000"

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
    global N, cK, cD
    f = open('test_data.pickle', 'rb')
    src = pickle.load(f)[-num:]
    f.close( )
    
    res = calculate(src, N, cK, cD)
    return [res[(i + 1 - 3) :i + 1] for i in range(3 - 1, len(res))]

def saveTestData(data):
    f = open('test_data.pickle', 'wb')
    pickle.dump(data, f)
    f.close( )

def saveStatus():
    global EACH_BIT, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS
    f = open('status.pickle', 'wb')
    pickle.dump([EACH_BIT, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS], f)
    f.close( )

def loadStatus():
    global EACH_BIT, TOTAL_ACCOUNT, TOTAL_AMOUNT, STATUS
    f = open('status.pickle', 'rb')
    data = pickle.load(f)
    f.close( )

    EACH_BIT = data[0]
    TOTAL_ACCOUNT = data[1]
    TOTAL_AMOUNT = data[2]
    STATUS = data[3]

def fetchCurrentPrice():
    try:
        req = urllib2.Request(CURRENT_PRICE_URL)
        response = urllib2.urlopen(req)
        resp_dict = json.loads(response.read())
    except :
        return None
    else:
        return resp_dict["ticker"]

################################################

def calculate(items, n, pk, pd):
    lastK = 50.0
    lastD = 50.0
    res = [];
    chunks = [items[(i + 1 - n) :i + 1] for i in range(n - 1, len(items))]
    for chunk in chunks:
        Ln = min([item['low'] for item in chunk])
        Hn = max([item['high'] for item in chunk])
        avg = np.mean([item['sell'] for item in chunk])
        rsv = (chunk[n - 1]['sell'] - Ln)/(Hn - Ln)*100
        lastK = pk*lastK + (1.0 - pk)*rsv
        lastD = pd*lastD + (1.0 - pd)*lastK
        J = 3.0*lastK - 2.0*lastD

        res.append({"K":lastK, "D":lastD, "J":J, "rsv":rsv, "avg":avg, "status":chunk[-1]})
    return res

LAST_PRICE = 0.0
def whatShouldDoNext(res):
    global LAST_PRICE, STATUS

    J = [item["J"] for item in res]
   # K = [item["J"] for item in res]
   # print("%f %f %F" %(J[-3], J[-2], J[-1]))

    avg = res[-1]["avg"]
    status = res[-1]["status"]
   # if J[-2] > 80 and K[-1] - J[-1] < 5 : #拐下
   #     return "sell"
   # if J[-2] < 20 and J[-3] > J[-2] and J[-2] < J[-1] and res[-1]["status"]["sell"] < avg: #拐上
   #     return "buy"
   # elif J[-2] > 80 and J[-3] < J[-2] and J[-2] > J[-1] and res[-2]["status"]["sell"] > avg: #拐下
   #     return "sell"
   # else:
   #     return "normal"

    if STATUS == 'buying' and LAST_PRICE - status["buy"] > 20:
        LAST_PRICE = 0.0
        return "sell"

    #LAST_PRICE = status["sell"] 

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
    global EACH_BIT
    global CURRENT_PRICE
    global LAST_PRICE

    CURRENT_PRICE = fetchCurrentPrice()
    LAST_PRICE = float(CURRENT_PRICE['sell'])

    if CURRENT_PRICE == None:
        return False
    TOTAL_ACCOUNT -= EACH_BIT*float(CURRENT_PRICE["buy"])
    TOTAL_AMOUNT += EACH_BIT

    log = "buy it at " + datetime.datetime.fromtimestamp(time.time()).strftime('%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    buy price: %f  |  current-amount: %f, current-account: %f\n" %(float(CURRENT_PRICE["buy"]), TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def sellIt():
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global EACH_BIT
    global CURRENT_PRICE
    CURRENT_PRICE = fetchCurrentPrice()
    if CURRENT_PRICE == None:
        return False
    TOTAL_ACCOUNT += EACH_BIT*float(CURRENT_PRICE["sell"])
    TOTAL_AMOUNT -= EACH_BIT

    log = "sell it at " + datetime.datetime.fromtimestamp(time.time()).strftime('%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    sell price: %f  |  current-amount: %f, current-account: %f\n" %(float(CURRENT_PRICE["sell"]), TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def testBuyIt(buy, time):
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global EACH_BIT
    global CURRENT_PRICE
    global LAST_PRICE

    CURRENT_PRICE = {"sell":buy}
    LAST_PRICE = float(buy)
    TOTAL_ACCOUNT -= EACH_BIT*float(buy)
    TOTAL_AMOUNT += EACH_BIT

    log = "buy it at " + datetime.datetime.fromtimestamp(time).strftime('%m/%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    buy price: %f  |  current-amount: %f, current-account: %f\n\n" %(buy, TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

def testSellIt(sell, time):
    global TOTAL_ACCOUNT
    global TOTAL_AMOUNT
    global EACH_BIT
    global CURRENT_PRICE

    CURRENT_PRICE = {"sell":sell}
    TOTAL_ACCOUNT += EACH_BIT*float(sell)
    TOTAL_AMOUNT -= EACH_BIT

    log = "sell it at " + datetime.datetime.fromtimestamp(time).strftime('%m/%d-%H:%M') + " | money: " + str(totalMoney()) + "\n"
    log += str("    sell price: %f  |  current-amount: %f, current-account: %f\n\n" %(sell, TOTAL_AMOUNT, TOTAL_ACCOUNT))

    print logv(log)
    return True

################################################

def main():
    global STATUS, CURRENT_PRICE
    while True:
        
        items = fetchData()
        if items == None:
            continue
        res = calculate(items[-100:], N, cK, cD)
        d('\n'.join([str("%f" %(a["J"])) for a in res]), 'J')
        command = whatShouldDoNext(res)
        if command == "buy":
            if STATUS != "buying" and buyIt(): 
                STATUS = "buying"
        elif command == "sell":
            if STATUS != "selling" and sellIt():
                STATUS = "selling"
        #buyIt()
        saveStatus()
        time.sleep(5)

def test():
    global STATUS, CURRENT_PRICE
    datas = loadTestData(200)
    times = []
    J = []
    DD = []
    K = []
    S = []
    A = []
    for data in datas:
        #print j(data)
        status = data[-1]['status'] 
        time = status['time']
        buy = (status['buy'] + status['sell'])/2.0
        sell = (status['sell'] + status['buy'])/2.0

        times.append(datetime.datetime.fromtimestamp(time).strftime('%d-%H:%M'))
        J.append(data[-1]['J'])
        DD.append(data[-1]['D'])
        K.append(data[-1]['K'])
        S.append(status['sell'])
        A.append(status['amount'])

        command = whatShouldDoNext(data)
        if command == "buy":
            if STATUS != "buying" and testBuyIt(buy, time): 
                STATUS = "buying"
        elif command == "sell":
            if STATUS != "selling" and testSellIt(sell, time):
                STATUS = "selling"

    KDJ = "\n".join([str("%s,%f,%f,%f,%f,%f" %(t, k, di, j, s, a)) for (k, di, j, t, s, a) in zip(K, DD, J, times, S, A)])
    d(KDJ, "test_data")

####################  main  #####################

loadStatus()
main()

#################### testing #####################

#saveTestData(fetchData())
#test()


