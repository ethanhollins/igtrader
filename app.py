from RootAccount import RootAccount
from Controller import Controller
from threading import Thread
import os
import json
import time


def runAccount(root_name, running_accounts):
	controller.running.append(RootAccount(controller, root_name, running_accounts))

if __name__ == '__main__':
	os.system('cls')

	global controller
	controller = Controller()

	if os.path.exists('info.json'):
		with open('info.json', 'r') as f:
			info = json.load(f)

		if 'running' in info:
			for i in info['running']:
				path = 'Accounts/{0}.json'.format(i)
				if os.path.exists(path):
					with open(path, 'r') as f:
						print('Starting {0} ({1}).'.format(i, ', '.join(info['running'][i])))
						t = Thread(target=runAccount, args=(i, info['running'][i]))
						t.start()
				else:
					print('Account {0} does not exist.'.format(i))

	controller.runQueue()

