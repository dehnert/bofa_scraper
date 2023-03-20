#!/usr/bin/env python3

import csv
import sys

import selenium

from bofa_scraper import BofAScraper

def connect(username):
	scraper = BofAScraper(
		username,
		None,
		timeout_duration=5, # Timeout to allow for page loads, defaults to 5s
		headless=False,		# Optional, defaults to True
		verbose=True,		# Optional, defaults to True
	)

	input("Hit enter when password entered: ")

	try:
		scraper.login() # Log in
	except selenium.common.exceptions.NoSuchElementException:
		input("Hit enter when logged in: ")
		scraper.check_login()

	return scraper

def handle_account(scraper, account):
	old = False
	new = True
	acct_scraper = scraper.open_account(account)
	while old != new:
		acct_scraper.scrape_transactions()
		acct_scraper.load_more_transactions()
		old = new
		new = acct_scraper.get_last_date()
		print(f"Last date now {new}")
	acct_scraper.close()

def save_transactions(account, outdir):
	filename = f"{outdir}/{account.get_name()}.csv"
	with open(filename, 'w') as fp:
		writer = csv.writer(fp)
		writer.writerow(['uuid', 'type', 'date', 'desc', 'amount'])
		for row in account.get_transactions():
			writer.writerow([row.uuid, row.type, row.date, row.desc, row.amount, ])

def handle_accounts(scraper, outdir):
	accounts = scraper.get_accounts()
	for account in accounts:
		try:
			handle_account(scraper, account)
		except NotImplementedError as exc:
			print("Ignoring NotImplementedError: ", exc)
			continue
		save_transactions(account, outdir)

def main(username, outdir):
	scraper = connect(username)
	handle_accounts(scraper, outdir)
	scraper.quit()

if __name__ == '__main__':
	main(sys.argv[1], sys.argv[2])

# vim: noexpandtab shiftwidth=4 softtabstop=4 tabstop=4
