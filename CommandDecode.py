import sys, re

"""
A basic class to retrieve command line arguments in a more friendly format

Created by Henry Hammond 2012
"""

class argvDecoder:
	
	def __init__(self):
		self.argv = sys.argv
		self.flags = self.getFlags()

	#This method decodes the command line arguments 
	def explodeArguments(self):
		
		commands = [ [v,self.argv.index(v)] for v in self.argv[1:] if v[0] == '-']
		counter = 0
		for cmd in commands:
			i = cmd[1]

			if counter < len(commands) -1:
				n = commands[counter+1][1]
			else:
				n = len(self.argv)
			commands[counter][0] = re.sub("^-{1,2}",'',cmd[0])
			commands[counter][1] = " ".join(self.argv[i:n][1:])
			counter+=1

		return commands

	#Check if string is a flag passed from command line
	def isFlag(self,command):
		return command in self.getFlags()

	def flags(self):
		return self.getFlags()

	#Get list of flags
	def getFlags(self):
		return [c[0] for c in self.explodeArguments()]

	#Get list of arguments
	def getArgument(self, command):
		return "".join([c[1] for c in self.explodeArguments() if c[0] == command])


	def explode(self):
		print self.explodeArguments()