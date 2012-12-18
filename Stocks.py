#!/usr/bin/python
# -*- coding: iso-8859-15 -*-

###############################################################################
#
#	Copyright (C) 2011  Henry Hammond
#	email: HenryHHammond92@gmail.com
#	
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU Lesser General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or any later
#	version.
#	
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#	
#	For a copy of the GNU Lesser General Public License, see
#	<http://www.gnu.org/licenses/>.
#
###############################################################################
#	
#	Please note that this software will modify files withing its directory,
#	it also assumes the existance of certain files (which it will generate if
#	absent from the system) to exist within a certain formatting. In the future
#	this software should be modified to rely on a more general and standardized
#	means of resource gathering. Please note that stocks.dat should be 
#	formatted such that each stock symbol needs to be on its own individidual 
#	line in order to properly be parsed. An exact example of this formatting is
#	included in triple quotes as follows:

"""
aapl
msft
goog
etc
"""

#	This software relies on online services (specifically Yahoo Finance's CSV
#	interface) which are subject to (and have been
#	known to) change at the discrecion of the respective parties. Should this 
#	occur please email me at the address above to inform me of the issue if it 
#	has not been addressed. 
#
###############################################################################


import urllib, string, os, sys, re, csv, sqlite3, cStringIO
from datetime import datetime
from operator import itemgetter

StockSourceFile	= 'stocks.dat'
defaultQuery	= 'sl1c1w1n'
defaultStocks = "aapl,msft,goog"
marketTime = {'open':0,'close':24}
defaultCache = 'cache.sqlite'
titleWidth = 8
yahooStockCommands = """
a	 Ask	 
a2	 Average Daily Volume	 
a5	 Ask Size
b	 Bid	 
b2	 Ask (Real-time)	 
b3	 Bid (Real-time)
b4	 Book Value	 
b6	 Bid Size	 
c	 Change & Percent Change
c1	 Change	 
c3	 Commission	 
c6	 Change (Real-time)
c8	 After Hours Change (Real-time)	 
d	 Dividend/Share	 
d1	 Last Trade Date
d2	 Trade Date	 
e	 Earnings/Share	 
e1	 Error Indication (returned for symbol changed / invalid)
e7	 EPS Estimate Current Year	 
e8	 EPS Estimate Next Year	 
e9	 EPS Estimate Next Quarter
f6	 Float Shares	 
g	 Day's Low	 
h	 Day's High
j	 52-week Low	 
k	 52-week High	 
g1	 Holdings Gain Percent
g3	 Annualized Gain	 
g4	 Holdings Gain	 
g5	 Holdings Gain Percent (Real-time)
g6	 Holdings Gain (Real-time)	 
i	 More Info	 
i5	 Order Book (Real-time)
j1	 Market Capitalization	 
j3	 Market Cap (Real-time)	 
j4	 EBITDA
j5	 Change From 52-week Low	 
j6	 Percent Change From 52-week Low	 
k1	 Last Trade (Real-time) With Time
k2	 Change Percent (Real-time)	 
k3	 Last Trade Size	 
k4	 Change From 52-week High
k5	 Percebt Change From 52-week High	 
l	 Last Trade (With Time)	 
l1	 Last Trade (Price Only)
l2	 High Limit	 
l3	 Low Limit	 
m	 Day's Range
m2	 Day's Range (Real-time)	 
m3	 50-day Moving Average	 
m4	 200-day Moving Average
m5	 Change From 200-day Moving Average	 
m6	 Percent Change From 200-day Moving Average	 
m7	 Change From 50-day Moving Average
m8	 Percent Change From 50-day Moving Average	 
n	 Name	 
n4	 Notes
o	 Open	 
p	 Previous Close	 
p1	 Price Paid
p2	 Change in Percent	 
p5	 Price/Sales	 
p6	 Price/Book
q	 Ex-Dividend Date	 
r	 P/E Ratio	 
r1	 Dividend Pay Date
r2	 P/E Ratio (Real-time)	 
r5	 PEG Ratio	 
r6	 Price/EPS Estimate Current Year
r7	 Price/EPS Estimate Next Year	 
s	 Symbol	 
s1	 Shares Owned
s7	 Short Ratio	 
t1	 Last Trade Time	 
t6	 Trade Links
t7	 Ticker Trend	 
t8	 1 yr Target Price	 
v	 Volume
v1	 Holdings Value	 
v7	 Holdings Value (Real-time)	 
w	 52-week Range
w1	 Day's Value Change	 
w4	 Day's Value Change (Real-time)	 
x	 Stock Exchange
y	 Dividend Yield
""".strip()

class BackupManager:

	def __init__(self,database='cache.sqlite'):
		self.database = database
		if not os.path.exists(database):
			self.createBackupDB()
		else:
			self.conn = sqlite3.connect(database)
			self.conn.text_factory = str

	def dbEncode(self, s):
		return s.replace('\'','\'\'')
	
	def dbDecode(self,s):
		return s.replace('\'\'','\'')

	def unpack(self, rows):
		dataList = []
		for row in rows:
			r = []
			for element in row:
				if type(element) == type(""):
					element = self.dbDecode(element)
				r.append(element)
			dataList.append(r)

		return dataList

	def createBackupDB(self):
		print "Building backup database"
		database = self.database
		if os.path.exists(database):
			os.remove(database)
		self.conn = sqlite3.connect(database)
		self.conn.text_factory = str
		c = self.conn.cursor()
		try:
			c.execute('CREATE TABLE backups ( time DATE PRIMARY KEY, day DATE, tags TEXT, data TEXT );');
			self.conn.commit()
		except Exception, e:
			print e

	def backup(self, CSV):
		CSV = self.dbEncode(CSV)
		c = self.conn.cursor()

		#generate tags
		tags = "".join([v for v in csv.reader(cStringIO.StringIO(CSV))][0])

		#write to database
		try:
			c.execute("INSERT INTO backups VALUES ( datetime('now','localtime'), date('now','utc'), ?, ?);", [tags,CSV] )
			self.conn.commit()
		except sqlite3.OperationalError, e:
			print 'Could not backup data:', e
			print 'Trying again'
			self.createBackupDB()
			self.backup(CSV)
		except sqlite3.IntegrityError:
			#non-unique update time
			pass

	def getFormattedBackups(self, date='',length=0):
		data = self.getCSVBackups(date)
		return [ r.split("\n",1)[0]+"\n"+StockManager().formatCSVData( "".join(r.split("\n",1)[1:]) , length=length) for r in data ]

	def getCSVBackups(self,date=''):
		c = self.conn.cursor();

		if date=='':
			databaseInput = c.execute('SELECT datetime(time,\'localtime\'), date(day,\'localtime\'),tags,data FROM backups ORDER BY time;')
		else:
			databaseInput = c.execute('SELECT datetime(time,\'localtime\'), date(day,\'localtime\'),tags,data FROM backups WHERE day=? ORDER BY time',date)

		databaseInput = self.unpack(databaseInput)

		records = []
		for row in databaseInput:
			date = row[0]	#Date data
			row = row[-1]	#CSV data
			records.append( "Record "+date+"\n"+row)

		return records

	def getToday(self):
		c = self.conn.cursor();
		d = self.unpack(c.execute('SELECT date(\'now\');'))
		return d[0]

	def getLatestTime(self):
		c = self.conn.cursor()
		try:
			data = c.execute('SELECT time FROM backups ORDER BY time');
			return data.fetchall()[-1][0]
		except:
			return []

	def getLatest(self,query='default',titles=True,length=0):
		data = self.getLatestCSV()
		time = self.getLatestTime();
		return "Latest Data: "+time+"\n"+StockManager(query=query,titles=titles).formatCSVData(data,length)

	def getLatestCSV(self):		
		backups = self.getCSVBackups()
		if backups != []:
			return "".join(self.getCSVBackups()[-1].split("\n",1)[1:])

		return "No backups available"

class StockManager:

	def __init__(self,query='default',titles=True,stocklist=[],caching=True,cacheFile='cache.csv'):
		if query == 'default':
			query = defaultQuery
		self.query = query
		self.titles = titles
		self.stocklist = stocklist
		self.caching = caching
		self.cacheFile = os.path.join(getModuleDirectory(),cacheFile)

	def getQuotes(self,stocks='default',tags='default',length=0):
		#set query based on input tags
		query = ''
		if tags != 'default':
			query = tags
		else:
			query = self.query

		#set stocklist based on input list
		if stocks != 'default':
			stocks = stocks.split(",")
			return self.doQuotes(query,self.titles,stocks,length)

		return self.doQuotes(query,self.titles,self.stocklist,length)

	def getYCommandDictionary(self):
		#Convert yahoo commands into useable python dictionary
		commands = [x.strip() for x in yahooStockCommands.split('\n') ]
		dictionary = {}
		for cmd in commands:
			cmd = cmd.split('\t')
			dictionary[cmd[0].strip()] = cmd[1].strip()
		
		return dictionary

	def getYCommands(self):
		commands = "".join([ cmd.split('\t')[0].strip() for cmd in yahooStockCommands.split('\n') ])
		return commands

	def stringToYCommand(self,str):
		#Reverse search text to yahoo symbol
		commands = [ cmd.strip() for cmd in yahooStockCommands.split('\n') ] 
		dictionary = {}
		for cmd in commands:
			cmd = cmd.split('\t')
			dictionary[cmd[1].strip()] = cmd[0].strip()
		return dictionary[str]

	def YCommandToString(self,str):
		#Search yahoo symbol to text
		commands = [ cmd.strip() for cmd in yahooStockCommands.split('\n') ]
		dictionary = {}
		for cmd in commands:
			cmd = cmd.split('\t')
			dictionary[cmd[0].strip()] = cmd[1].strip()
		return dictionary[str]


	def downloadStocks(self,stocks=[],inTags="sl1c1w1n"):
		#get data from yahoo server

		#split query tags
		tags = self.splitTags(inTags)
		
		if type(stocks) == type(''):
			stocks = stocks.split(",")
		#Create url query
		url = "http://download.finance.yahoo.com/d/quotes/csv?s=%s&f=%s"%( "+".join(stocks), inTags)

		try:
			#Get file from yahoo and feed into csv reader
			csvdata = csv.reader(urllib.urlopen(url))
			
			#Format data into dictionary with tags and pass it on
			data = []
			for row in csvdata:
				dictionary = {}
				for i in range(len(tags)):
					dictionary[ tags[i] ] = row[i]

				data.append(dictionary)
			return data
		except IOError, e:
			print "Unable to access online servers."
			return []

	def doQuotes(self,query,titles,stocks,length=0):

		#get quote data
		quoteDictionary = self.downloadStocks(stocks,query)
		#format data
		formattedData = self.formatFromDictionary(quoteDictionary,query,titles,titleLen=length)

		#chache data to a file
		if self.caching:
			self.saveQuoteDictionary(quoteDictionary,query,self.cacheFile)

		#return formatted quote data
		return formattedData

	def getCSVData(self,stocks='default',query='default'):
		if stocks == 'default':
			stocks = defaultStocks
		if query == 'default':
			query = defaultQuery

		return self.createCSVData( self.downloadStocks(stocks,query),query )

	def saveQuoteDictionary(self,quoteDictionary,query,fpath):

		#generate CSV data
		csvContent = self.createCSVData(quoteDictionary,query)

		#write data to file
		if os.path.exists(fpath):
			os.remove(fpath)
		file = open(fpath,'w')
		file.write(csvContent)
		file.close()

	def createCSVData(self,quoteDictionary,query):
		#Split query into tags
		tags = self.splitTags(query)

		#create arrays from dictionaries
		vals = []
		for row in quoteDictionary:
			vrow = []
			for tag in tags:
				vrow.append( row[tag] )
			vals.append(vrow)

		dataBuffer = cStringIO.StringIO()
		writer = csv.writer( dataBuffer )

		#put tags at top row of file
		writer.writerow(tags)
		#write remainder of file
		for v in vals: writer.writerow(v)

		data = dataBuffer.getvalue()
		dataBuffer.close()
		return data

	def formatCSVData(self,data,length=0):
		dataBuffer = cStringIO.StringIO(data)
		reader = csv.reader(dataBuffer)
		rawData = [r for r in reader]

		dictionary = []
		for row in rawData[1:]:	#skip tag row at top
			rowDictionary = {}
			for i in range(len(rawData[0])):
				rowDictionary[ rawData[0][i] ] = row[i]
			dictionary.append(rowDictionary)
		formattedData = StockManager().formatFromDictionary(dictionary,"".join(rawData[0]),titleLen=length)

		return formattedData

	def getSavedCSVData(self,filepath):
		#check if file exists
		if os.path.exists(filepath):

			#split csv data
			values = [value for value in csv.reader(open(filepath,'r')) ]
			
			#try reading data
			try:
				queryTags = [ re.sub("\W",'',value) for value in values[0] ]
				data = []
				for value in values[1:]:
					row = {}
					for tag in range(len(queryTags)):
						row[queryTags[tag]] = value[tag]
					data.append(row)
				return [queryTags]+[data]
			except IndexError:
				#the file had no data rows...
				return []
		#file did not exist
		return []

	def splitTags(self,query):
		return re.findall("[a-z]\d?",query.lower())

	def formatFromDictionary(self,inputDictionary,sortOrder='sl1cw1n',titles=True,delimiter=" | ",titleLen=0,titleRows=2):
		
		#sort input data by first tag
		inputDictionary = sorted(inputDictionary,key=itemgetter(self.splitTags(sortOrder)[0]))	
		
		#order tags by sort order and then leftover tags
		order = self.splitTags(sortOrder)
		dictionaryTags = [ tag for tag in inputDictionary[0]]
		tags = [ tag for tag in order if tag in dictionaryTags ] + [tag for tag in dictionaryTags if tag not in order]
		
		#populate rows array from dictionary
		rows = []
		for row in inputDictionary:
			rowdata = []
			for tag in tags:
				rowdata.append( row[tag] )
			rows.append(rowdata)
		
		#special case: left justify symbols
		if 's' in tags:
			for row in rows:
				row[tags.index('s')] = row[tags.index('s')].ljust(4)
		
		#place command row at top of data list
		rows = [["(%s)"%(tag) for tag in tags]] + rows
		if titles == True:
			if titleLen == 0:
				rows = [[self.YCommandToString(t) for t in tags]] + rows
			else:
				rows = [[self.YCommandToString(t)[0:titleLen] for t in tags]] + rows
		
		#format all data into a table
		table = self.formatAsTable(rows,delimiter,titles,titleRows)
		return table

	def formatAsTable(self,inputArray,delimiter=' | ',titles=True,titleRows=1):
		
		#set table dimensions
		tableColLength = len(inputArray[0])
		tableRowLength = len(inputArray)
		
		#create blank table
		table = []
		
		for row in range(tableRowLength):
			table.append([])
			for col in range(tableColLength):
				table[row].append('')
		if titles:
			table.append([])
			for col in range(tableColLength):
				table[tableRowLength].append('')
		
		#find longest value in each col and normalize col to that size
		for col in range(tableColLength):
			maxLength = 0	# <- longest cell length
			
			for row in range(tableRowLength):
				if len(inputArray[row][col]) > maxLength:
				 maxLength = len(inputArray[row][col])
			
			#apply formatting to cells
			for row in range(tableRowLength):
				if row < titleRows and titles:
					newData = inputArray[row][col].center(maxLength)
				else:
					newData = inputArray[row][col].rjust(maxLength)
				table[row][col] = newData
			#add line to bottom of table for later use
			if titles:
				#create dashed line...
				table[tableRowLength][col] = "".zfill(maxLength).replace('0',u'-')
#Unicode: U+25A6, UTF-8: E2 96 A6
		#create new blank table
		#TODO: come back and fix this so we don't need a new table...
		newTable = [[]]
		for row in range(tableRowLength):
			newTable.append([])
			for c in range(tableColLength):
				newTable[row].append('')
		if titles == True:
			newTable.append([])
			for c in range(tableColLength):
				newTable[tableRowLength].append('')
		
		#populate new table with values from old table and reorder with delimiters, etc
		for i in range(titleRows):
			newTable[i] = table[i]
		newTable[titleRows] = table[-1]
		newTable[titleRows+1:] = table[titleRows:-1]

		return "\n".join( [ delimiter.join(row) for row in newTable ] ) 


def getStockList(file):
	#load stock list from given filepath
	try:
		f = open(file,'r')
		data = f.read().split('\n')
		f.close()
		return sorted(data)
	except:
		return defaultStocks.split(',');

def getModuleDirectory():
	if( sys.argv[0] == 'Stocks.py' ):
		#we are in directory
		return '.'
	else:
		#return the path to this module's directory
		return sys.argv[0][0:sys.argv[0].rindex(os.path.sep)+1]

def isTradingTime(tradingTime={'open':8,'close':16}):
	#for use with automated updates
	currentTime = datetime.now()
	if currentTime.hour >= tradingTime['open'] and currentTime.hour <= tradingTime['close']:
		return True
	return False

def getStockList(file):
	#load stock list from given filepath
	try:	
		f = open(file,'r')
		data = f.read().split('\n')
		data = sorted(data)
		f.close()
		return data
	except IOError, e:
		return defaultStocks.split(",")

class argvDecoder:
	
	def __init__(self):
		self.argv = sys.argv
		self.flags = self.getFlags()

	def expandArgs(self):
		
		args = [ [v,sys.argv.index(v)] for v in sys.argv[1:] if v[0] == '-']
		counter = 0
		for cmd in args:
			i = cmd[1]

			if counter < len(args) -1:
				n = args[counter+1][1]
			else:
				n = len(sys.argv)
			args[counter][0] = re.sub("^-{1,2}",'',cmd[0])
			args[counter][1] = " ".join(sys.argv[i:n][1:])
			counter+=1

		return args

	def isFlag(self,command):
		return command in self.getFlags()

	def flags(self):
		return self.getFlags()

	def getFlags(self):
		return [command[0] for command in self.expandArgs()]

	def getFlag(self, flag):
		return "".join([command[1] for command in self.expandArgs() if command[0] == flag])

	def explode(self):
		print self.expandArgs()

if __name__ == "__main__":

	query = defaultQuery
	stockListPath = os.path.join(getModuleDirectory(),StockSourceFile)

	#Decode command line arguments
	argList = argvDecoder()

	#Title width
	if argList.isFlag('w'):
		titleWidth = int(argList.getFlag('w'))

	#Query arguments
	if 'q' in argList.getFlags():
		query = argList.getFlag('q')

	#stock list
	if argList.isFlag('s') and argList.isFlag('stockFile'):
		stockListPath = argList.getFlag('stockFile')
		stockList = getStockList(stockListPath)
		stockList = stockList + argList.getFlag('s').split(' ')

	elif argList.isFlag('s'):
		stockList = []+argList.getFlag('s').split(' ')

	elif argList.isFlag('stockFile'):
		stockListPath = argList.getFlag('stockFile')
		StockSourceFile = argList.getFlag('stockFile')
		if not (stockListPath[0:2] in ['./','~/'] or stockListPath[0] == '/'):
			stockListPath = os.path.join(getModuleDirectory(),StockSourceFile)
		stockList = getStockList(stockListPath)

	else:
		stockList = getStockList(stockListPath)

	#caching
	if argList.isFlag('caching'):
		caching = True
		if argList.isFlag('cacheFile'):
			defaultCache = argList.getFlag('cacheFile')
	else:
		caching = False

	#titles enabled?
	if argList.isFlag('titles-off'):
		titles = False
	else:
		titles = True

	defaultStocks = stockList
	defaultQuery  = query

	backup = BackupManager( os.path.join(getModuleDirectory(), defaultCache) )

	if isTradingTime(marketTime):
		stocks = StockManager(query,stocklist=stockList,caching=False)
		data = stocks.getCSVData()
		loadingError = False;
		try:
			print stocks.formatCSVData(data,length=titleWidth)
		except IndexError:
			loadingError = True
			print backup.getLatest(length=titleWidth)
		except Exception, e:
			print e

		if data != backup.getLatestCSV() and not loadingError and caching:
				backup.backup(data)

	else:
		try:
			print "".join(backup.getLatest(length=titleWidth).split("\n",1)[1:])

		except Exception:
			#no backup files exist
			stocks = StockManager(query,stocklist=stockList,caching=False)
			data = stocks.getCSVData()
			
			try:
				print stocks.formatCSVData(data,length=titleWidth)
			except Exception, e:
				print e

			try:
				if data != backup.getLatestCSV():
					backup.backup(data)
			except:
				#file not found exception
				pass

	state = ''
	if not isTradingTime(marketTime):
		state = '(Markets closed)'

	now = datetime.now()
	lastBackup = backup.getLatestTime()
	print "last update %s - last backup %s" % (now.strftime("%H:%M:%S").rstrip('0'),lastBackup)
	print state
