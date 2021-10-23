#!/usr/bin/python3
# Mirrorscript v2 By Hazmirul Afiq
import subprocess, requests, re, sys
import operator
import argparse, apt, os
import threading
from shutil import copyfile

result_url = []
ping_result = []
mirrors = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}

class fetch_thread(threading.Thread):	
	def __init__(self, count, url,schema):
		threading.Thread.__init__(self)
		self.count = count + 1
		self.url = url
		self.schema = schema

	def run(self):
		try:
			response = requests.get(self.schema+self.url, headers=headers).status_code
			if response == 200:
				result_url.append(self.url)
			else:
				print("[!] " + self.url + " doesn't support " + self.schema)
		except Exception as e:
			print("[!] Failed to establish a connection to host " + self.schema + self.url)

def fetch_url(urls,schema):
	threads = []	
	for count, url in enumerate(urls):
		count = fetch_thread(count, url,schema)
		threads.append(count)

	for i in threads:
		i.start()

	for i in threads:
		i.join()

	return result_url

def ask(question,default):
	yes = set(['yes','y','ye'])
	no = set(['no','n'])
	yes.add('') if default == 'y' else no.add('')
	while True:
		choice = input(question + " Default [" + default + "]: ").lower()
		if choice in yes:
			return True
		elif choice in no:
			return False
		else:
			print("\t    Please answer with [y] or [n]: ");

class ping_thread(threading.Thread):
	def __init__(self, count, hostname):
		super(ping_thread, self).__init__()
		self.count = count + 1
		self.hostname = hostname

	def run(self):
		p = subprocess.Popen(['ping','-c 3', self.hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
		p = [str(x.decode('utf-8')) for x in p]

		if not p[0].strip():
			# error
			print("\t[!] Error: Something went wrong ...")
			print("\t    " + p[1].strip())
			response = ask("\t   Stuck at finding mirror latency. Do you want to retry[y] or skip[n]?",'n')
			if response:
				run(self.hostname)
		else:
			try:
				if "100% packet loss" in p[0].strip():
					average = "[!] Unable to check " + self.hostname + " latency, potentially host block ICMP request."
				else:
					average = p[0].strip().splitlines()[7].split('=')[1].split('/')[1]
					mirrors[self.hostname] = str(str(average).zfill(7))
			except Exception as e:
				if not ask("\t[!] Something went wrong. would you like to try again [y] or [n].",'y'):
					print ("\t    Exiting ...\n")
					sys.exit(1)
			if verbose:
				print("\t- {0:30} : {1}".format(self.hostname,average))

def ping_s(hostname):
	threads = []
	for count, hostname in enumerate(hostname):
		count = ping_thread(count, hostname)
		threads.append(count)

	for i in threads:
		i.start()

	for i in threads:
		i.join()

	return ping_result


if __name__ == "__main__":

	# Check if user is root first.
	if os.getuid() != 0:
		sys.exit("[!] Must run as root/sudo\n")

	# Argument parser
	parser = argparse.ArgumentParser(description='Kali Mirrorscripts-v2 by IceM4nn automatically select the best kali mirror server and apply the configuration')
	parser.add_argument('-v','--verbose', help='enable verbose output', action="store_true")
	parser.add_argument('-https', help='use HTTPS in apt transport (default HTTP)', action="store_true")
	parser.add_argument('-src', help='enable sources packages (default disable)', action="store_true")
	args = parser.parse_args()

	# Initialize arguments
	https = True if args.https else False
	verbose = True if args.verbose else False
	sources = True if args.src else False

	# Banner
	print("#")
	print("# Mirrorscripts-v2 - By Hazmirul Afiq")
	print("# Automatically select the best Kali mirror and apply the configuration")
	print("# https://github.com/IceM4nn/mirrorscript-v2")
	print("# https://www.metahackers.pro/speed-kali-linux-update/")
	print("#\n")

	if https:
		cache = apt.Cache()
		cache.open()

		package = "apt-transport-https" 
		print("[-] Checking if '" + package + "' package is installed.")
		try:
			if cache[package].is_installed:
				if verbose:
					print("\t- "+package+" is installed\n")
			else:
				print("\t! "+package+" is NOT installed. Attempting to install ...")
				cache[package].mark_install()
				print("\t- Installing "+package+"\n")
				try:
					cache.commit()
					print("\n\t- "+package+" installed succesfully")
				except Exception as e:
					print("\t! package "+package+" is failing to install")
					print("\t  "+str(e))
					sys.exit(1)
		except KeyError as e:
			print("[!] The package \"" + package + "\" could not found in local apt cache. You may need to install it manually later after you've done update kali.")
			print("    For the time being, re-run the script without https support.")
			sys.exit(1)

	print("[+] Getting mirror list ...")
	response = requests.get('https://http.kali.org/README.mirrorlist', headers=headers).text
	urls = re.findall(r'(?:href="http(?:s|))(.*)(?:/README")',response)[2:]
	
	if verbose:
		print("[+] Found (" + str(len(urls)) + ") lists of mirrors:")
		for url in urls:
			print("\t- https" + url)
		print("")

	print("[+] Checking mirrors ...")
	schema = 'https' if https else 'http'
	new_urls = fetch_url(urls,schema)

	print("[+] Finding the best latency")

	hosts = []
	for hostname in new_urls:
		hostname = hostname.split("//")[-1].split("/")[0].split('?')[0]
		hosts.append(hostname)
	
	# sending ping in threads
	ping_s(hosts)	

	if verbose:
		print("")

	# sorted to fastest mirror
	sorted_mirrors = sorted(mirrors.items(), key=operator.itemgetter(1))
	print("[+] Fastest mirror: " + str(sorted_mirrors[0]))

	print("[+] Preparing ...")

	# Making backup
	if verbose:
		print("\t- Making a backup file /etc/apt/sources.list.bk ...")

	copyfile('/etc/apt/sources.list', '/etc/apt/sources.list.bk')

	if verbose:
		print("\t- Checking sources.list for older entries ...")

	contents = []
	file = open("/etc/apt/sources.list", "r+")
	if verbose:
		print("\t- Commenting older entries ...")
	i = 0
	for line in file.readlines():
		if (re.search(r'^deb http(?:s|)://http\.kali\.org/kali', line, re.I)) or (re.search(r'^deb-src http(?:s|)://http\.kali\.org/kali', line, re.I)):
			newline = "#" + line
			file.write(newline)
			contents.append(newline)
		elif re.search(r'^# Autogenerated script by MirrorScripts-V2', line, re.I):
			print("\t! Found previous applies! Commenting it out ...")
			contents.append(line)
			i = 1
		elif i == 1:
			if not line.startswith("#"):
				newline = "#" + line
				file.write(newline)
				contents.append(newline)
			else:
				contents.append(line)
			i = i+1
		elif i == 2:
			if not line.startswith("#"):
				newline = "#" + line
				file.write(newline)
				contents.append(newline)
			else:
				contents.append(line)
			i = 0
		else:
			contents.append(line)
	file.seek(0)
	file.truncate()
	file.seek(0)
	for line in contents:
		file.write(line)
	file.close()
	if verbose:
		print("\t- Done\n")

	print("[+] Updating sources.list with new entry ...")
	
	matching = [s for s in urls if sorted_mirrors[0][0] in s]
	new_mirror = schema + matching[0]
	if verbose:
		print("\t- Your new mirror: " + new_mirror + "\n")

	temp = "sh -c \'echo \"\n# Autogenerated script by MirrorScripts-V2\" >> /etc/apt/sources.list\'"
	subprocess.Popen(temp, shell=True, stdout=subprocess.PIPE).stdout.read()

	line = "deb " + new_mirror + " kali-rolling main contrib non-free"
	temp = "sh -c \'echo %s >> /etc/apt/sources.list\'"
	subprocess.Popen(temp % line, shell=True, stdout=subprocess.PIPE).stdout.read()

	line = "deb-src " + new_mirror + " kali-rolling main contrib non-free"
	if not sources:
		line = "#" + line
	temp = "sh -c \'echo \"%s\" >> /etc/apt/sources.list\'"
	subprocess.Popen(temp % line, shell=True, stdout=subprocess.PIPE).stdout.read()

	print("[+] Done!")
	if verbose:
		print("\t- Run 'sudo apt clean; sudo apt update' for the changes to load.\n")
	else:
		print("")
