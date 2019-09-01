from RootAccount import RootAccount
from Controller import Controller
import os
import json


if __name__ == '__main__':
	os.system('cls')

	if os.path.exists('info.json'):
		with open('info.json', 'r') as f:
			info = json.load(f)

		running = []
		if 'running' in info:
			for i in info['running']:
				path = 'Accounts/{0}.json'.format(i)
				if os.path.exists(path):
					with open(path, 'r') as f:
						print('Starting {0} ({1}).'.format(i, ', '.join(info['running'][i])))
						running.append(RootAccount(i, info['running'][i]))
				else:
					print('Account {0} does not exist.'.format(i))

		Controller(running)
