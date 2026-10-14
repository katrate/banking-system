import bank_system as bank

bank.boot()
bank.precheck_run("prequel.sql")
bank.ensure_schema()
bank.ensure_admin()

if not bank.admin_login():
    raise SystemExit

customer_menu = [
    ("Add customer", bank.add_customer),
    ("Find customer by account number", bank.find_customer),
]
account_menu = [
    ("New transaction (deposit / withdraw / transfer)", bank.transaction),
    ("View account / mini statement", bank.view_account),
]
loan_menu = [
    ("Apply for loan", bank.loan),
    ("Pay loan EMI", bank.loan_payment),
    ("View loan status", bank.view_loan),
]
admin_menu = [
    ("Add admin", bank.add_admin),
]

while True:
    bank.clear()
    bank.header()
    print(bank.center("===== BANKING SYSTEM ====="))
    print(bank.center("  1) Customer Management"))
    print(bank.center("  2) Accounts & Transactions"))
    print(bank.center("  3) Loan Management"))
    print(bank.center("  4) Admin Management"))
    print(bank.center("  0) Exit"))
    try:
        choice = bank.get_int("Choose an option: ")
    except (KeyboardInterrupt, EOFError):
        choice = 0

    if choice == 0:
        bank.spinner("Shutting down", 1, 0.1)
        bank.type_print("Goodbye!", 0.03)
        bank.conn.close()
        break
    if choice == 1:
        bank.run_submenu("Customer Management", customer_menu)
    elif choice == 2:
        bank.run_submenu("Accounts & Transactions", account_menu)
    elif choice == 3:
        bank.run_submenu("Loan Management", loan_menu)
    elif choice == 4:
        bank.run_submenu("Admin Management", admin_menu)
    else:
        print("  Invalid choice.")
