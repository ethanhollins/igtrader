from RootAccount import RootAccount
from Controller import Controller
from threading import Thread
import os
import json
import time


def runAccount(idx, root_name, running_accounts):
	acc = RootAccount(controller, idx, root_name, running_accounts)
	
	if root_name != 'backtester': 
		controller.running.append(acc)
		controller.run_next = True
		acc.runloop()
	else:
		os._exit(1)

if __name__ == '__main__':
	os.system('cls')

	global controller
	controller = Controller()

	if os.path.exists('info.json'):
		with open('info.json', 'r') as f:
			info = json.load(f)

		if 'running' in info:
			count = 0
			for i in info['running']:
				while not controller.run_next:
					time.sleep(1)
					pass
					
				path = 'Accounts/{0}.json'.format(i)
				if os.path.exists(path):
					with open(path, 'r') as f:
						print('Starting {0} ({1}).'.format(i, ', '.join(info['running'][i])))
						t = Thread(target=runAccount, args=(count, i, info['running'][i]))
						t.start()
				else:
					print('Account {0} does not exist.'.format(i))

				count += 1
				controller.run_next = False

			controller.runQueue()

