"""Archive-it.
Usage:
	archive_it.py file <url> [--frequency=<x>]
	archive_it.py site <url> [--frequency=<x>] [--follow-links]
	archive_it.py magnet <url> 
	archive_it.py -h | --help
	archive_it.py --version
"""
from docopt import docopt

if __name__=='__main__':
	arguments = docopt(__doc__, version='Archive-it 0.1')
	print arguments

def archive_file(url, x, option1):
	print "Downloading file: %s"%url
def archive_site(url, x, option1):
	print "Downloading site: %s"%url
def archive_magnet(url, x, option1):
	print "Downloading magnet: %s"%url

scripts={ 'file': archive_file,
	  'site': archive_site,
	  'magnet': archive_magnet
}
for i in 'file', 'site', 'magnet':
	if(arguments[i]):
		scripts[i](arguments['<url>'], arguments['--frequency'], arguments['--follow-links'])
