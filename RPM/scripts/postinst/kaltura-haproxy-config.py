#!/usr/bin/python
import sys
import os.path
from shutil import copy2
from os import symlink

# VERBOSE = True # Not being used yet
VERSION = "0.03"

## This dictionary holds the values needed in the answer file. The configuration will not begin 
## if one is missing, unless excluded in the exclusion list below (ANSWER_FILE_EXCLUDE_LIST). 
## The value is the mapping the for needed pattern whcih needs to be used for parsing. "" means just use the answer file value as it is.
ANSWERFILE_VARS = {
	"HAPROXY_USE_BACKEND_NAME"	: "",
	"HAPROXY_HTTPS_CERT"	:	"",
	"HAPROXY_ACL_KMS"		:	"ACL_SERVER_KMS",
	"HAPROXY_ACL_KMC"		:	"ACL_SERVER_KMC",
	"HAPROXY_ACL_KAC"		:	"ACL_SERVER_KAC",
	"HAPROXY_ACL_KSS"		:	"ACL_SERVER_KSS",
	"HAPROXY_ACL_CDN"		:	"ACL_SERVER_CDN",
	"HAPROXY_BACKEND_HOST_KMC_SERVER" : "GENERAL_BACKEND",
	"HAPROXY_BACKEND_HOST_KMS_SERVER" : "GENERAL_BACKEND",
	"HAPROXY_BACKEND_HOST_CDN_SERVER" : "GENERAL_BACKEND",
	"HAPROXY_BACKEND_HOST_KAC_SERVER" : "GENERAL_BACKEND",
	"HAPROXY_BACKEND_HOST_KSS_SERVER" : "GENERAL_BACKEND",
	"HAPROXY_BACKEND_HOST_KCW_SERVER" : "KCW_BACKEND",
}

# List here all the vars which are optional. This means that should one of the following
# be missing from the answer file, it will not fail, but simply not be incouded in the conf file
ANSWER_FILE_EXCLUDE_LIST = [
	"BACKEND_HOST_CDN",
	"BACKEND_HOST_CDN_SERVER",
	"BACKEND_HOST_KSS",
	"BACKEND_HOST_KSS_SERVER",
	"HAPROXY_ACL_KMS",
	# "HAPROXY_ACL_SECTION",
]


# Note that this is the pattern in which the configuration line vars in the config files follow. Order matters.
# In case you need to add / remove a value from the line pattern, this is the place to go. Failure to parse the line will cause the script to fail.
PATTERNS = {
	"GENERAL_BACKEND" : [
		"NAME", 
		"NUMBERING", 
		"IP-RANGE" , 
		"MAXCONNECTION_VALUE", 
		"OPTIONAL_VALUES", 
	],

	"KCW_BACKEND" : [
		"NAME",
		"NUMBERING", 
		"IP-RANGE",
		"OPTIONAL_VALUES", 
		"MAXCONNECTION_VALUE",
	],
}

# Single line patterns. Basically 
CONFIG_LINE_TEMPLATE = {
	"GENERAL_BACKEND" 	: "server 	NAME IP-RANGE:PORT cookie COOKIE maxconn MAXCONNECTION_VALUE OPTIONAL_VALUES",
	"KCW_BACKEND" 		: "server   NAME IP-RANGE:PORT OPTIONAL_VALUES maxconn MAXCONNECTION_VALUE",
	"ACL_SERVER_KMS"	: "acl host_kms hdr(host) -i DOMAIN",
	"ACL_SERVER_KAC"	: "acl host_kac hdr(host) -i ACL_SERVER_KAC",
	"ACL_SERVER_KSS"	: "acl host_kss hdr(host) -i ACL_SERVER_KSS",
	"ACL_SERVER_CDN"	: "acl host_cdn hdr(host) -i ACL_SERVER_CDN",
	"ACL_SERVER_KMC"	: "acl host_kmc hdr(host) -i ACL_SERVER_KMC",
	"USE_BACKEND"		: "use_backend BACKEND_PROPERTY if host_PROPERTY",
}

# Paths of the config template after RPM deployment and after the script is run
SOURCE_TEMPLATE_PATH="/tmp/"
DESTINATION_TEMPLATE_PATH="/tmp/"
CONFIG_TEMPLATE_FILE="haproxy.cfg.template"
CONFIG_DESTINATION_FILE="haproxy.cfg"

# Functions -------------------------------------------------------------------------------------------------------------------------------------

# Simple file open, and returns handle or None if there's a problem
def open_file(file_name):
	try:
		# print os.path.isfile(file_name)
		if os.path.isfile(file_name):
			file_handle = open(file_name, 'r')
			return file_handle;
		else:
			print "The file " + file_name + " does not exist."
			return None
	except IOError:
		print "Problem reading the " + file_name + " file."
		return None

# Write a string (not a list!) to a given file.
def write_text_to_file(file_name, text):
	try:
		file_handle = open(file_name, 'w')
		file_handle.write (text)
		return True
	except:
		print "Problem writing to " + file_name + "."
		return False		

# Returns a dictionary of the 
def read_answer_file(file_handle):
	answerFile_content = {}
	try:
		for line in file_handle:
			tmpLine = line.strip('\r\n').split('=')
			answerFile_content[ tmpLine[0] ] = tmpLine[1]
		return answerFile_content
	except:
		print "There was a problem reading the file."
		return None

# Checks if there are no mandatory files missing from the answer file
def check_answer_file_vars(answerFile_content_di, needed_val_list):
	ok_flag = True

	var_check_list = []
	# creating a list with the vars which are mandatory
	for var in ANSWERFILE_VARS.keys():
		if var not in ANSWER_FILE_EXCLUDE_LIST:
			var_check_list.append(var)

	answer_keys = answerFile_content_di.keys()
	missing_vars = []
	for var in var_check_list:
		match = [s for s in answer_keys if var in s] # produces a list with the needed vars
		ok_flag = False
		for item in match:
			if item.find(var) == 0:
				ok_flag = True
	
		if ok_flag == False:
			missing_vars.append(var)

	if len(missing_vars):
		print "The following variables are missing:"
		for index in missing_vars:
			print index
		return False
	return True
				

# Reads and returns the config template into a list
def load_config_template(file_name):
	try:
		file_content_list = open_file(file_name)
		if file_content_list != None:
			# for line in file_content_list:
				# print line,
			return file_content_list
		except:
			print "There was a problem reading the file."
			return None		



# Simple file copy
def copy_template_file(source, destination):
    try:
        shutil.copy(source, destination)
        return True
    # will be thrown if source and destination are the same file
    except shutil.Error as error:
        print('Error: %s' % error)
        return False
    # will be thrown if source or destination doesn't exist
    except IOError as error:
        print('Error: %s' % error.strerror)
        return False


# Returns a given list to a formatted string. Usable for writing lists to files
def list_to_text(text_list):
	return_string = ""
	for item in text_list:
		return_string += item.strip('\n')
	return return_string



# Placing the logrotate configuration
def place_logrotate_config_file():
	LOGROTATE_CONFIG_FILE = "/etc/logrotate.d/haproxy"
	LOGROTATE_CONFIG_CONTENT = """/var/log/haproxy/haproxy.log {
	rotate 7
	daily
	missingok
	compress
	dateext
	notifempty
}"""
	if not (write_text_to_file('/tmp/TEST', LOGROTATE_CONFIG_CONTENT) ):
		print "Logrotate configuration was not placed."
		return False
	else:
		print "Logrotate configuration placed at " + LOGROTATE_CONFIG_FILE
		return True

# Placing the monit configuration
def place_monit_config_file():
	MONIT_FILE_NAME = "haproxy.rc"
	MONIT_CONFIG_FILE = "/opt/kaltura/app/configurations/monit/monit.avail/"+MONIT_FILE_NAME
	MONIT_LINK_FILE = "/opt/kaltura/app/configurations/monit/monit.d/enabled"+MONIT_FILE_NAME
	MONIT_CONFIG_CONTENT = """check process haproxy
           with pidfile "/opt/kaltura/log/haproxy/haproxy.pid"
           start program = "/etc/init.d/haproxy restart" with timeout 60 seconds
           stop program = "/etc/init.d/haproxy stop"
           group kaltura
           depends on haproxy_conf

        check file haproxy_conf
            with path "/etc/haproxy/haproxy.cfg"
            if changed checksum
               then exec "/etc/init.d/haproxy restart"
	"""	
	if not (write_text_to_file('/tmp/MONIT', MONIT_CONFIG_CONTENT) ):
		print "Logrotate configuration was not placed."
		return False
	else:
		symlink(MONIT_CONFIG_FILE, MONIT_LINK_FILE)
		print "Logrotate configuration placed at " + MONIT_CONFIG_FILE
		return True


# String manipulation and parsing of the given values in the answer file. Nothing changes in the answer file. Only the string constructs are returned as a dictionary
def construct_config_line(setting_line_key, setting_line_content):
	setting_line_content = setting_line_content.strip('"')
	line_list = []

	# Backend server parsing
	if ( setting_line_key.find("SERVER") != -1 ):
		# print "SERVER FOUND"
		config_vars = setting_line_content.split(',')
		template = ANSWERFILE_VARS[setting_line_key]
		cookie_name = setting_line_key.split('_')[3]
		temp_line_dict = {}
		for index in range (len (config_vars)):
			# print PATTERNS[template][index], config_vars[index]
			temp_line_dict [PATTERNS[template][index]] = config_vars[index].strip('"')

		altered_template = CONFIG_LINE_TEMPLATE[template].strip('"') # Approriate template assignment

		ip_class = temp_line_dict["IP-RANGE"].split('.')	# Used temorarily just for split
		ip_class = ip_class[0] + '.' + ip_class[1]+'.' + ip_class[2]+'.' # reassigning with the values
		# print ip_class
		if (temp_line_dict["IP-RANGE"].find('-') != (-1) ):
			# print "RANGE FOUND:" + temp_line_dict["IP-RANGE"]
			temp_split_var = temp_line_dict["IP-RANGE"].split('.')[3].split('-') # splitting according to '.' and then picking the last octate for parsing

			range_begin = int(temp_split_var[0])
			range_end = int(temp_split_var[1])
			loop_top = range_end - range_begin
		else:
			range_begin = int(temp_line_dict["IP-RANGE"].split('.')[3])
			loop_top = 0 # meaning that there is no "range" to be walked upon
			
		server_name_num = int (temp_line_dict["NUMBERING"])

		for num in range (0,loop_top+1):
			ip_octate = str(range_begin + num)
			server_serial_id = str(server_name_num + num)
		
			for val in PATTERNS[template]:
				# print val
				if val == "NAME":
					altered_template = altered_template.replace (val, temp_line_dict[val]+server_serial_id)
				elif val == "IP-RANGE":
					altered_template = altered_template.replace (val, ip_class+ip_octate)
				elif val == "MAXCONNECTION_VALUE":
					altered_template = altered_template.replace (val, temp_line_dict[val])
				else:
					altered_template = altered_template.replace (val, temp_line_dict[val])

			altered_template = altered_template.replace ("COOKIE", cookie_name+server_serial_id)
			if (cookie_name not in ("KCW","KSS")):
				altered_template = altered_template.replace ("PORT", "80")
			elif (cookie_name == "KSS"):
				altered_template = altered_template.replace ("PORT", "88")
			elif (cookie_name == "KCW"):
				altered_template = altered_template.replace ("PORT", "1935")
			
			# print altered_template
			line_list.append(altered_template)
			altered_template = CONFIG_LINE_TEMPLATE[template].strip('"') # reseting the string for each repeated line
			# Backend server parsing ends here-----------------------------------------------------------------------------

	elif ( setting_line_key.find("_ACL_") != (-1) ):
		# print "ACL FOUND"
		altered_template =  CONFIG_LINE_TEMPLATE[ANSWERFILE_VARS[setting_line_key]]
		altered_template = altered_template.replace (ANSWERFILE_VARS[setting_line_key], setting_line_content)
		# print altered_template
		line_list.append(altered_template)
	else:
		# print "ELSE:"+setting_line_content
		line_list.append(setting_line_content)

	return line_list

# Replacing string for string and returning the changed list
def config_template(template_content_list, line_dict):
	altered_lines = []
	for line in template_content_list:
		if line.count('@') == 2:
			extracted_key = line.split('@')[1]
			line = line.replace('@','')
			for val in line_dict[extracted_key]:
				# print line.replace(extracted_key, val),
				altered_lines.append( line.replace(extracted_key, val), ) 
			# print "-------------------------------------------------------------------------------------------"
		else:
			altered_lines.append( line )
	return altered_lines
	
def usage():
	print """
	kaltura-haproxy-config.py <answer file location>

	"""

# Main ------------------------------------------------------------------------------------------------------------------------------------------

if len (sys.argv) != 2: 
	print "USAGE"
else:
	answerFIle_name = sys.argv[1]

handle = open_file(answerFIle_name)
if (handle != None):
	# Reading and checking needed values exist in the answer file
	answer_file_dict = read_answer_file(handle)
	if (check_answer_file_vars( answer_file_dict, ANSWERFILE_VARS ) == False):
		print "\nPlease verify that all the needed information is defined in the answer file."
		exit (1)

	replacing_value_dict = {}
	# for key in ANSWERFILE_VARS.keys():
	relevant_answer_vars = [string for string in answer_file_dict if "HAPROXY" in string] # Creating a list with the haproxy vars

	for var in relevant_answer_vars:
		replacing_value_dict[var] =  construct_config_line(var, answer_file_dict[var])


	file_content = load_config_template(SOURCE_TEMPLATE_PATH+CONFIG_TEMPLATE_FILE)
else:
	exit (1)

## Uncomment for printing of the altered data and keys on the screen (before the replacement)
# for line in file_content:
# 	print line,
# for key in replacing_value_dict.keys():
# 	print key, "->",
# 	print
# 	for line in replacing_value_dict[key]:
# 		print line

 # actual template line replacement takes place here
final_template = config_template(file_content, replacing_value_dict)

if write_text_to_file (DESTINATION_TEMPLATE_PATH+CONFIG_DESTINATION_FILE, "".join(final_template)):
	if not place_monit_config_file() or place_logrotate_config_file:
		return 1

