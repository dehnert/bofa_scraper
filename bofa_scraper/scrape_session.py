from datetime import datetime
from decimal import Decimal

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select

from .account import Account, Transaction
from .util import Log, Timeout

class ScrapeSessionBase:
	driver: webdriver.Firefox
	account: Account

	def __init__(self, driver: webdriver.Firefox, account: Account):
		self.driver = driver
		self.account = account

		Log.log('Starting scraping session for account %s' % account.get_name())
		url = self.account.get_element().find_element(By.TAG_NAME, "a").get_attribute("href")
		self.driver.execute_script('window.open()')
		self.driver.switch_to.window(self.driver.window_handles[1])
		self.driver.get(url)
		Timeout.timeout()
		Log.log('Tab opened for account %s' % account.get_name())

	def close(self):
		Log.log('Closing tab for account %s...' % self.account.get_name())
		self.driver.close()
		self.driver.switch_to.window(self.driver.window_handles[0])
		Log.log('Closed')

	def scrape_transactions(self):
		raise NotImplemented("must implement scraper")

	def load_more_transactions(self):
		raise NotImplemented("must implement scraper")

	def get_last_date(self):
		"""Return the last date covered.

		This helps support workflows like "keep calling load_more_transactions
		until we hit 2022".

		Account types using a fixed date window (for example, showing one
		statement at a time) rather than the last N transactions should override
		this and base the value on the actual window used."""
		transactions = self.account.get_transactions()
		return min(t.get_date() for t in transactions)

	@classmethod
	def get_scraper(cls, driver: webdriver.Firefox, account: Account):
		if 'Banking' in account.get_name():
			return ScrapeSessionBank(driver, account)
		elif 'Visa Signature' in account.get_name():
			return ScrapeSessionCredit(driver, account)
		else:
			raise NotImplementedError("unknown account type: " + account.get_name())

class ScrapeSessionBank(ScrapeSessionBase):
	def __init__(self, driver: webdriver.Firefox, account: Account):
		super().__init__(driver, account)

	def scrape_transactions(self):
		Log.log('Scraping bank transactions for account %s...' % self.account.get_name())
		i: int = 0
		out: list[Transaction] = []
		row: WebElement
		for row in self.driver.find_elements(By.CLASS_NAME, "activity-row"):
			transaction = Transaction()
			transaction.amount = float(row.find_element(By.CLASS_NAME, "amount-cell").text.replace(",","").replace("$",""))
			transaction.date = row.find_element(By.CLASS_NAME, "date-cell").text
			transaction.desc = row.find_element(By.CLASS_NAME, "desc-cell").text.replace("\nView/Edit","")
			transaction.type = row.find_element(By.CLASS_NAME, "type-cell").text
			transaction.uuid = row.get_attribute("class").split(" ")[1]
			out.append(transaction)
			i = i + 1
		Log.log('Found %d transactions on account %s' % (i, self.account.get_name()))
		self.account.set_transactions(out)
		return self

	def load_more_transactions(self):
		Log.log('Loading more transactions in account %s...' % self.account.get_name())
		view_more = self.driver.find_element(By.CLASS_NAME, "view-more-transactions")
		self.driver.execute_script("arguments[0].click();", view_more)
		Timeout.timeout()
		Log.log('Loaded more transactions in account %s' % self.account.get_name())
		return self

class ScrapeSessionCredit(ScrapeSessionBase):
	def __init__(self, driver: webdriver.Firefox, account: Account):
		super().__init__(driver, account)

	def scrape_transactions(self):
		Log.log('Scraping credit transactions for account %s...' % self.account.get_name())
		out: list[Transaction] = []
		row: WebElement
		rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody.trans-tbody-wrap tr")
		Log.log('Found %d rows on account %s' % (len(rows), self.account.get_name()))
		for row in rows:
			def fetch_amount(html_class):
				text = row.find_element(By.CLASS_NAME, html_class).text
				return Decimal(text.replace(",", "").replace("$", ""))
			transaction = Transaction()
			transaction.date = row.find_element(By.CLASS_NAME, 'trans-date-cell').text
			transaction.desc = row.find_element(By.CLASS_NAME, 'trans-desc-cell').text
			transaction.amount = fetch_amount('trans-amount-cell')
			transaction.balance = fetch_amount('trans-balance-cell')
			trans_type = row.find_element(By.CSS_SELECTOR, '.trans-type-cell div')
			type_prefix = 'icon-type-'
			trans_types = [t[len(type_prefix):] for t in trans_type.get_attribute('class').split()
			                                    if t.startswith(type_prefix)]
			if trans_types:
				transaction.type = trans_types[-1]
			else:
				transaction.type = None
			transaction.uuid = ""
			#transaction.uuid = row.get_attribute("class").split(" ")[1]
			print(transaction)
			out.append(transaction)
		Log.log('Found %d transactions on account %s' % (len(out), self.account.get_name()))
		self.account.extend_transactions(out)
		return self

	def load_more_transactions(self):
		Log.log('Loading more transactions in account %s...' % self.account.get_name())
		try:
			view_more = self.driver.find_element(By.LINK_TEXT, "Previous transactions")
		except selenium.common.exceptions.NoSuchElementException:
			print("Out of transactions")
			return self
		self.driver.execute_script("arguments[0].click();", view_more)
		Timeout.timeout()
		Log.log('Loaded more transactions in account %s' % self.account.get_name())
		return self

	def get_last_date(self):
		select_element = self.driver.find_element(By.ID, 'goto_select_trans_top')
		select = Select(select_element)
		date = select.first_selected_option.text
		if date == "Current transactions":
			return datetime.now()
		else:
			return datetime.strptime(date, '%B %d, %Y')

	# Download QFX:
	# https://secure.bankofamerica.com/myaccounts/details/card/download-transactions.go?&adx=a7d23276ba86338b55b8052e2d4ffc7e221b8613b45841edad06cc9c31b5fa42&stx=1c9bf82c781cdc8ad4d3e608f00c0e03dd14acb5b1e6c224912e17b94ed7fc51&target=downloadStmtFromDateList&formatType=qfx
	# First chunk is select_transaction values
	# Last bit is just "&formatType=qfx" (from select_filetype, but can hardcode)
	# format_type=csv would be good too
	# Accessing just downloads it, with a reasonable name


# vim: noexpandtab shiftwidth=4 softtabstop=4 tabstop=4
