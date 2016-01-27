from subprocess import check_output
import argparse
import sys, os



#OPTION PARSER
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source",help="Path to the root of the source code to be scanned")
parser.add_argument("-e","--exclude",help="File: list of excludes (one per line)")
parser.add_argument("-v","--verbose",help="Turn on verbosity", action="store_true")
parser.add_argument("-u","-url","--url",help="The url for the cloud scan controller")
parser.add_argument("-n","--name",help="Name of the project")
parser.add_argument("-q","--quiet",help="Name of the project")
parser.add_argument("-m","--memory",help="Max memory to be used for translation (DEFAULT is 2G)")
parser.add_argument("-upload","--upload",help="Do you want to upload the fpr to the SSC",action="store_true")
parser.add_argument("-sscurl","--sscurl",help="URL of the SSC server (required if you choose the -upload option")
parser.add_argument("-sscuser","--sscuser",help="Username for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscpass","--sscpass",help="Password for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscproject","--sscproject",help="Exact(case sensitive) project name for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscversion","--sscversion",help="Exact(case sensitive) version name for the SSC server (required if you choose the -upload option")
args=parser.parse_args()

def getArgs():
	data = {}
	data["isQuiet"] = False
	data["hasExcludes"]=False
	data["isVerbose"]=False
	data["willUpload"]=False
	if args.sscurl:
		data["willUpload"] = True
		if not args.sscurl or not args.sscuser or not args.sscpass or not args.sscproject or not args.sscversion:
			print "You are trying to upload the results to the SSC. This option requires the -sscurl, -sscuser, -sscpass, -sscproject, and -sscversion"
			print "If you are not trying to upload the results to the SSC, please use --url instaed of --sscurl and specify the cloudscan controller url"
			sys.exit()
		else:
			data["sscurl"] = args.sscurl 
			data["sscuser"] = args.sscuser
			data["sscpass"] = args.sscpass
			data["sscproject"] = args.sscproject
			data["sscversion"] = args.sscversion 
	else:
		if not args.url:
			print "You must specify the cloud controler url with the -url option or the -upload option to upload to the SSC"
			sys.exit()
		else:
			data["controllerUrl"] = args.url

	if args.verbose:
		data["isVerbose"]=True
	data["sourcePath"] = args.source
	if not data["sourcePath"].endswith("/"):
		data["sourcePath"] = data["sourcePath"] + "/"
	if not os.path.isdir(data["sourcePath"]):
		print data["sourcePath"] + " is not a valid source directory."
		sys.exit()

	if args.memory:
		data["maxmem"] = args.memory
	else:
		data["maxmem"] = "2"
	data["maxmem"] = "-Xmx"+data["maxmem"] + "G"
	if args.name:
		data["buildName"] = args.name
	else:
		print "You must specify a build name  with the -n or --name option"
		sys.exit()

	if args.exclude:
		data["excludeFile"]=args.exclude
		data["hasExcludes"]=True
		try:
			with open(str(data["excludeFile"]),"r") as EF:
				content=EF.read()
			data["excludeArray"] = content.split("\n")
		#print excludeArray
		except:
			print "Could not open or read exclude file."
	return data

##CLEAN THE BUILD
def cleanBuild(data):
	print "[+] CLEANING THE BUILD"
	try:
		out = check_output(["sourceanalyzer","-b",str(data["buildName"]),"-clean"])
	except:
		print "Could not clean the project. Something is wrong"
		sys.exit()


##TRANSLATE THE BUILD 
def translateBuild(data):
	print "[+] TRANSLATING THE BUILD"
	if data["hasExcludes"]:
		command = ["sourceanalyzer","-b",data["buildName"],data["sourcePath"]]
		x=""
		for ex in data["excludeArray"]:
			if ex != "":
				command.append("-exclude")
				command.append(data["sourcePath"] + ex)
		command.append(data["maxmem"])
		
		try:
			#print command
			out = check_output(command)
		except:
			print "Could not translate build. Something is wrong 1"
			sys.exit()
	else: ##NO exceptions
		command = ["sourceanalyzer","-b",data["buildName"],data["sourcePath"],data["maxmem"]]
		try:
			#print command
			out = check_output(command)
		except:
			print "Could not translate build. Something is wrong 2"
			sys.exit()

	command = ["sourceanalyzer","-b",data["buildName"],"-show-files"]
	print "Number of files : ",
	try:
		out = check_output(command)
		y = out.split("\n")
		i = 0 
		for each in y:
			i+=1
		print str(i)
	except:
		print "[-] File Count Failed"
	print "Lines of Code : ",
	try:
		command = ["sourceanalyzer","-b",data["buildName"],"-show-loc"]
		out = check_output(command)
		loc = out.split(": ")
		print loc[1]
	except:
		print "[-] LOC count Failed"

## EXPORT BUILD SESSION 
def exportBuild(data):
	print "[+] EXPORTING BUILD SESSION"
	try:
		mbs=data["buildName"].strip()+".mbs"
		command = ["sourceanalyzer","-b",data["buildName"],"-export-build-session",mbs]
		out = check_output(command)
	except:
		print "[-] Mobile Build Session Failed"
		sys.exit()

def getProjectList(data):
	data["sscurl"] = "\""+ data["sscurl"] + "\""
	command = ["fortifyclient","listProjectVersions","-url",data["sscurl"],"-user",data["sscpass"],"-password",data["sscuser"]]
	try:
		out = check_output(command)
	except:
		print "[-] Could not get a list of projects"
		sys.exit()
	projectList = out.split("\n")
	versionid = ""
	for project in projectList:
		if data["sscproject"] in str(project):
			print "Matched Project ",
			print data["sscproject"]
			if data["sscversion"] in str(project):
				print "Matched Version ",
				print data["sscversion"]
				projectDetails = str(project).split("\t")
				versionid=str(projectDetails[0])
				print "Using Version ID " + versionid
	if versionid == "":
		print "Couldnt find the SSC project."
		sys.exit()
	return versionid

def getUploadToken(data):
	command = ["fortifyclient","token","-gettoken","AnalysisUploadToken","-url",data["sscurl"],"-user",data["sscuser"],"-password",data["sscpass"]]
	try:
		out = check_output(command)
		x = out.split("Token:")
		uploadtoken= str(x[1])
	except:
		print "Couldnt get the upload token"
		sys.exit()
	return uploadtoken

def getAuthToken(data):
	command = ["fortifyclient","token","-gettoken","CloudCtrlToken","-url",sdata["sscurl"],"-user",data["sscuser"],"-password",data["sscpass"]]
	try:
		out = check_output(command)
		x = out.split("Token:")
		authtoken= str(x[1])
	except:
		print "Couldnt get the Auth Token"
		sys.exit()
	return authtoken

	## SEND TO CLOUD
def scanInCloud(data):
	mbs=data["buildName"].strip()+".mbs"
	fpr=data["buildName"].strip()+".fpr"

	if not data["willUpload"]:
		print "[+] SENDING TO CLOUD SCANNER (this may take a while)"
		data["controllerUrl"] = "\""+ data["controllerUrl"] + "\""
		command = ["cloudscan","-url",data["controllerUrl"],"start","-block","-o","-f",fpr,"-mbs",mbs,"-scan"]
		try:
			out = check_output(command)
			print out 
		except:
			print "Couldnt submit the job to the cloudscanner"
			sys.exit()
		out = check_output(["rm",mbs])
	else:
		print "[+] SENDING TO CLOUD SCANNER (this may take a while)"
		versionid = getProjectList(data)
		uploadtoken = getUploadToken(data)
		authtoken = getAuthToken(data)

		command = ["cloudscan","-sscurl",sdata["sscurl"],"-ssctoken",authtoken.strip(),"start","-upload","-versionid",versionid,"-mbs",mbs,"-uptoken",uploadtoken.strip(),"-scan","-Xmx4G"]
		try:
			out = check_output(command)
			print out 
		except:
			print "Couldnt submit the job to the cloudscanner"
			sys.exit()

		out = check_output(["rm",mbs])


def main():
	data = getArgs()
	for k,v in data.iteritems():
		print k, 
		print "\t\t\t",
		print v
	print ""
	cleanBuild(data)
	translateBuild(data)
	exportBuild(data)
	scanInCloud(data)


if __name__ == "__main__":
    main()
