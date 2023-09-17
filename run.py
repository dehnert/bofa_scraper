#!/usr/bin/env python3

import csv
import sys

from requestium import Session
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

def handle_account(scraper, session, outdir, account):
	old = False
	new = True
	acct_scraper = scraper.open_account(account)
	saved_files = False
	while old != new:
		acct_scraper.scrape_transactions()
		acct_scraper.load_more_transactions()
		old = new
		new = acct_scraper.get_last_date()
		print(f"Last date now {new}")
		if hasattr(acct_scraper, 'save_files'):
			# We try this every screen because apparently sometimes (when there
			# are no transactions in the current month?) the Download link
			# doesn't appear on a screen.
			if not saved_files:
				saved_files = acct_scraper.save_files(session, outdir)
	acct_scraper.close()
	if not saved_files:
		print("Never succeeded in saving files")

def save_transactions(account, outdir):
	transactions = account.get_transactions()
	if not transactions:
		print(f"No transactions for {account.get_name()}")
		return
	filename = f"{outdir}/{account.get_name()}.csv"
	with open(filename, 'w') as fp:
		writer = csv.writer(fp)
		writer.writerow(['uuid', 'type', 'date', 'desc', 'amount'])
		for row in account.get_transactions():
			writer.writerow([row.uuid, row.type, row.date, row.desc, row.amount, ])

def handle_accounts(scraper, outdir):
	accounts = scraper.get_accounts()
	session = Session(driver=scraper.driver)
	session.transfer_driver_cookies_to_session()
	for account in accounts:
		try:
			handle_account(scraper, session, outdir, account)
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
