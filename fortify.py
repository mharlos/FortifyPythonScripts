from subprocess import check_output
import argparse
import sys, os


#GLOBALS
global hasExcludes
global isVerbose
global willUpload
hasExcludes = False
isVerbose = False
willUpload = False

#OPTION PARSER
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source",help="Path to the root of the source code to be scanned")
parser.add_argument("-e","--exclude",help="File: list of excludes (one per line)")
parser.add_argument("-v","--verbose",help="Turn on verbosity", action="store_true")
parser.add_argument("-u","--url",help="The url for the cloud scan controller")
parser.add_argument("-n","--name",help="Name of the project")
parser.add_argument("-upload","--upload",help="Do you want to upload the fpr to the SSC",action="store_true")
parser.add_argument("-sscurl","--sscurl",help="URL of the SSC server (required if you choose the -upload option")
parser.add_argument("-sscuser","--sscuser",help="Username for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscpass","--sscpass",help="Password for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscproject","--sscproject",help="Exact(case sensitive) project name for the SSC server (required if you choose the -upload option")
parser.add_argument("-sscversion","--sscversion",help="Exact(case sensitive) version name for the SSC server (required if you choose the -upload option")
parser.add_argument("-m","--memory",help="Max memory to be used for translation (DEFAULT is 2G)")
args=parser.parse_args()

if args.upload:
	willUpload = True
	if not args.sscurl or not args.sscuser or not args.sscpass or not args.sscproject or not args.sscversion:
		print "You are trying to upload the results to the SSC. This option requires the -sscurl, -sscuser, -sscpass, -sscproject, and -sscversion"
		sys.exit()
	else:
		sscurl = args.sscurl 
		sscuser = args.sscuser
		sscpass = args.sscpass
		sscproject = args.sscproject
		sscversion = args.sscversion 
else:
	if not args.url:
		print "You must specify the cloud controler url with the -url option or the -upload option to upload to the SSC"
		sys.exit()
	else:
		controllerUrl = args.url

if args.verbose:
	isVerbose=True
sourcePath = args.source
if args.memory:
	maxmem = args.memory
else:
	maxmem = "2"
maxmem = "-Xmx"+maxmem + "G"
if args.name:
	buildName = args.name
else:
	print "You must specify a build name  with the -n or --name option"
	sys.exit()

if args.exclude:
	excludeFile=args.exclude
	hasExcludes=True
	try:
		with open(excludeFile,"r") as EF:
			content=EF.read()
		excludeArray = content.split("\n")
		print excludeArray
	except:
		print "Could not open or read exclude file."


##CLEAN THE BUILD
print "Cleaning Build\t\t",
try:
	out = check_output(["sourceanalyzer","-b",buildName,"-clean"])
except:
	print "Could not clean the project. Something is wrong"
	sys.exit()
print "DONE"


##TRANSLATE THE BUILD 
print "Translating Build\t\t",
if hasExcludes:
	command = ["sourceanalyzer","-b",buildName,sourcePath]
	x=""
	for ex in excludeArray:
		if ex != "":
			command.append("-exclude")
			command.append(sourcePath + ex)
	command.append(maxmem)
	
	#print command 

	#out=check_output([test])
	try:
		out = check_output(command)
	except:
		print "Could not translate build. SOmething is wrong"
		sys.exit()
else:
	command = ["sourceanalyzer","-b",buildName,sourcePath,maxmem]
	try:
		out = check_output(command)
	except:
		print "Could not translate build. SOmething is wrong"
		sys.exit()

command = ["sourceanalyzer","-b",buildName,"-show-files"]
print "Number of files : ",
try:
	out = check_output(command)
	y = out.split("\n")
	i = 0 
	for each in y:
		i+=1
	print i
except:
	print "File Count Failed"
print "Lines of Code : ",
try:
	command = ["sourceanalyzer","-b",buildName,"-show-loc"]
	out = check_output(command)
	print out
except:
	print "LOC count Failed"

## EXPORT BUILD SESSION 
print "Exporting Build Session \t\t",
try:
	mbs=buildName.strip()+".mbs"
	command = ["sourceanalyzer","-b",buildName,"-export-build-session",mbs]
	out = check_output(command)
	print "DONE"
except:
	print "Mobile Build Session Failed"
	sys.exit()

## SEND TO CLOUD
if willUpload == False:
	print "Sending build to cloud scaner (this may take a while)"
	#try:
	mbs=buildName.strip()+".mbs"
	fpr=buildName.strip()+".fpr"
	controllerUrl = "\""+ controllerUrl + "\""
	command = ["cloudscan","-url",controllerUrl,"start","-block","-o","-f",fpr,"-mbs",mbs,"-scan"]
	print command 
	out = check_output(command)
	print out 
	out = check_output(["rm",mbs])
	
else:
	print "Sending build to cloud scaner (this may take a while)"
	mbs=buildName.strip()+".mbs"
	fpr=buildName.strip()+".fpr"

	sscurl = "\""+ sscurl + "\""

	command = ["fortifyclient","listProjectVersions","-url",sscurl,"-user",sscuser,"-password",sscpass]
	try:
		out = check_output(command)
	except:
		print "Could not get a list of projects"
		sys.exit()
	x = out.split("\n")
	versionid = ""
	for each in x:
		if sscproject in str(each):
			print "Match Project"
			if sscversion in str(each):
				print "Match Version"
				y = str(each).split("\t")
				versionid=str(y[0])
				print "Using Version ID " + versionid
	if versionid == "":
		print "Couldnt find the SSC project."

	command = ["fortifyclient","token","-gettoken","AnalysisUploadToken","-url",sscurl,"-user",sscuser,"-password",sscpass]
	try:
		out = check_output(command)
		x = out.split("Token:")
		uploadtoken= str(x[1])
	except:
		print "Couldnt get the upload token"
		sys.exit()

	command = ["fortifyclient","token","-gettoken","CloudCtrlToken","-url",sscurl,"-user",sscuser,"-password",sscpass]
	try:
		out = check_output(command)
		x = out.split("Token:")
		authtoken= str(x[1])
	except:
		print "Couldnt get the Auth Token"
		sys.exit()


	command = ["cloudscan","-sscurl",sscurl,"-ssctoken",authtoken.strip(),"start","-upload","-versionid",versionid,"-mbs",mbs,"-uptoken",uploadtoken.strip(),"-scan","-Xmx4G"]
	try:
		out = check_output(command)
		print out 
	except:
		print "Couldnt submit the job to the cloudscanner"
		sys.exit()

	out = check_output(["rm",mbs])


