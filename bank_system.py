import os
import hashlib
import calendar
import getpass
import time
from datetime import date

import mysql.connector

#region Config
def load_env(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ[key.strip()] = val.strip()

load_env()
#endregion

#region Connection
conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "katrate"),
    password=os.getenv("DB_PASSWORD", "hello"),
)
#endregion

#region Schema Setup
def precheck_run(path):
    cursor = conn.cursor()
    with open(path, "r") as f:
        sql_text = f.read()
    for stmt in sql_text.split(";"):
        lines = []
        for l in stmt.splitlines():
            if not l.strip().startswith("--"):
                lines.append(l)
        clean = "\n".join(lines).strip()
        if clean:
            cursor.execute(clean)
    conn.commit()
    cursor.close()

def ensure_column(cursor, table, column, definition):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (table, column),
    )
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + definition)

def ensure_schema():
    c = conn.cursor()
    ensure_column(c, "loans", "loan_type", "VARCHAR(30) DEFAULT 'PERSONAL'")
    ensure_column(c, "loans", "purpose", "VARCHAR(255) NULL")
    ensure_column(c, "loans", "last_payment_date", "DATE NULL")
    ensure_column(c, "loans", "next_due_date", "DATE NULL")
    conn.commit()
    c.close()
#endregion

#region Helpers
def next_id(cursor, table, id_col, prefix, width=4):
    cursor.execute("SELECT " + id_col + " FROM " + table + " WHERE " + id_col + " LIKE %s",
                   (prefix + "-%",))
    max_num = 0
    for row in cursor.fetchall():
        val = row[id_col] if isinstance(row, dict) else row[0]
        try:
            max_num = max(max_num, int(val.split("-")[1]))
        except (IndexError, ValueError, TypeError):
            continue
    return prefix + "-" + str(max_num + 1).zfill(width)

def get_text(prompt, required=True):
    while True:
        val = input(center_prompt(prompt)).strip()
        if not required:
            return val or None
        if val:
            return val
        say("This field cannot be empty.")

def get_int(prompt):
    while True:
        try:
            return int(input(center_prompt(prompt)).strip())
        except ValueError:
            say("Please enter a whole number.")

def get_float(prompt):
    while True:
        try:
            return float(input(center_prompt(prompt)).strip())
        except ValueError:
            say("Please enter a number.")

def get_amount(prompt):
    while True:
        try:
            val = float(input(center_prompt(prompt)).strip())
            if val <= 0:
                say("Amount must be greater than zero.")
                continue
            return round(val, 2)
        except ValueError:
            say("Please enter a valid number.")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def calc_emi(principal, annual_rate, months):
    r = annual_rate / 12 / 100
    if r == 0:
        return round(principal / months, 2)
    emi = principal * r * (1 + r) ** months / ((1 + r) ** months - 1)
    return round(emi, 2)

def add_months(d, months):
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)

def _account_info(cursor, account_number):
    cursor.execute(
        "SELECT a.balance, a.status, a.account_type, c.name "
        "FROM accounts a JOIN customers c ON a.customer_ID = c.customer_ID "
        "WHERE a.account_number = %s",
        (account_number,),
    )
    return cursor.fetchone()

def _record(cursor, account_number, tx_type, amount, new_balance,
            sender_id=None, sender_name=None, receiver_id=None, receiver_name=None):
    txn_id = next_id(cursor, "transactions", "transaction_ID", "TXN", 5)
    cursor.execute(
        "INSERT INTO transactions "
        "(transaction_ID, account_ID, type, amount, balance_after, "
        "receiver_ID, receiver_Name, sender_ID, sender_Name) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (txn_id, account_number, tx_type, amount, new_balance,
         receiver_id, receiver_name, sender_id, sender_name),
    )
    cursor.execute("UPDATE accounts SET balance=%s WHERE account_number=%s",
                   (new_balance, account_number))
    return txn_id
#endregion

#region Animations
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def term_width():
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80

def center(text):
    return text.center(term_width())

def center_prompt(text):
    pad = max(0, (term_width() - len(text)) // 2)
    return " " * pad + text

def header():
    print()
    print(center("=" * 52))
    print(center("B A N K I N G   M A N A G E M E N T"))
    print(center("S Y S T E M   v 1 . 0"))
    print(center("=" * 52))
    print()

def say(text):
    print(center(text))

def say_block(lines):
    if not lines:
        return
    longest = max(len(l) for l in lines)
    pad = max(0, (term_width() - longest) // 2)
    for l in lines:
        print(" " * pad + l)

def type_print(text, delay=0.03):
    for ch in center(text):
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def ring_loader(label="", rounds=3, delay=0.13):
    frames = ["◝", "◞", "◟", "◜"]
    for i in range(rounds * len(frames)):
        frame = frames[i % len(frames)]
        text = frame if not label else frame + "  " + label
        print("\r" + center(text), end="", flush=True)
        time.sleep(delay)
    print()

def loading(label, n=3, delay=0.25):
    for i in range(n + 1):
        print("\r" + center(label + " " + "." * i), end="", flush=True)
        time.sleep(delay)
    print("\r" + center(label + " OK"))

def spinner(label, rounds=2, delay=0.1):
    frames = "|/-\\"
    for i in range(rounds * 4):
        print("\r" + center(label + " " + frames[i % 4]), end="", flush=True)
        time.sleep(delay)
    print("\r" + center(label + " Done!"))

def progress(label, steps=20, delay=0.04):
    for i in range(steps + 1):
        bar = "#" * i + "-" * (steps - i)
        pct = int(i * 100 / steps)
        print("\r" + center(label + " [" + bar + "] " + str(pct) + "%"), end="", flush=True)
        time.sleep(delay)
    print()

def boot():
    clear()
    header()
    ring_loader("", rounds=2, delay=0.14)
    clear()
    progress("Initialising", 18, 0.03)
    loading("Loading modules", 3, 0.22)
    spinner("Connecting to database", 2, 0.09)
    loading("Preparing menu", 2, 0.22)
    print()
#endregion

#region Admin Login
def ensure_admin():
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        aid = next_id(c, "admins", "admin_ID", "ADM")
        c.execute("INSERT INTO admins (admin_ID, username, password_hash, full_name) "
                  "VALUES (%s,%s,%s,%s)",
                  (aid, "admin", hash_pw("admin123"), "System Administrator"))
        conn.commit()
        say("Default admin created  ->  username: admin   password: admin123")
    c.close()

def admin_login():
    clear()
    header()
    print(center("===== ADMIN LOGIN ====="))
    for _ in range(3):
        user = get_text("Username: ")
        pw = getpass.getpass(center_prompt("Password: ")).strip()
        spinner("Verifying credentials", 2, 0.1)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password_hash, full_name FROM admins WHERE username=%s", (user,))
        row = cursor.fetchone()
        cursor.close()
        if row and row["password_hash"] == hash_pw(pw):
            type_print("Access granted. Welcome, " + (row["full_name"] or user) + "!", 0.03)
            time.sleep(0.6)
            clear()
            header()
            return True
        type_print("Access denied. Try again.", 0.02)
    type_print("Too many failed attempts. Exiting.", 0.02)
    return False

def add_admin():
    print("\n" + center("--- Add New Admin ---"))
    username = get_text("New admin username: ")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM admins WHERE username=%s", (username,))
    if c.fetchone()[0] > 0:
        say("Username '" + username + "' already exists.")
        c.close()
        return
    full_name = get_text("Full name (optional): ", required=False)
    pw = getpass.getpass(center_prompt("Password for new admin: ")).strip()
    if not pw:
        say("Password cannot be empty.")
        c.close()
        return
    pw2 = getpass.getpass(center_prompt("Confirm password: ")).strip()
    if pw != pw2:
        say("Passwords do not match.")
        c.close()
        return
    aid = next_id(c, "admins", "admin_ID", "ADM")
    try:
        c.execute("INSERT INTO admins (admin_ID, username, password_hash, full_name) "
                  "VALUES (%s,%s,%s,%s)",
                  (aid, username, hash_pw(pw), full_name))
        conn.commit()
        say("Admin created : " + aid + "  (username: " + username + ")")
    except mysql.connector.Error as e:
        conn.rollback()
        say("Error creating admin: " + str(e))
    finally:
        c.close()
#endregion

#region Features
def add_customer():
    print("\n" + center("--- Add New Customer ---"))
    name = get_text("Customer name: ")
    email = get_text("Email (optional): ", required=False)
    phone = get_text("Phone (optional): ", required=False)
    address = get_text("Address (optional): ", required=False)
    say("Account type:  1) SAVINGS   2) CURRENT   3) FIXED")
    acct_type = {"1": "SAVINGS", "2": "CURRENT", "3": "FIXED"}.get(
        get_int("Choose (1-3): "), "SAVINGS")

    cursor = conn.cursor()
    cust_id = next_id(cursor, "customers", "customer_ID", "CUS")
    acct_no = next_id(cursor, "accounts", "account_number", "ACC")
    try:
        cursor.execute(
            "INSERT INTO customers (customer_ID, name, email, phone, address) "
            "VALUES (%s,%s,%s,%s,%s)",
            (cust_id, name, email, phone, address))
        cursor.execute(
            "INSERT INTO accounts (account_number, customer_ID, account_type, balance) "
            "VALUES (%s,%s,%s,0.00)",
            (acct_no, cust_id, acct_type))
        conn.commit()
        say("Customer created : " + cust_id)
        say("Account opened   : " + acct_no + "  (" + acct_type + ", balance 0.00)")
    except mysql.connector.Error as e:
        conn.rollback()
        say("Error adding customer: " + str(e))
    finally:
        cursor.close()

def _customer_report(acct):
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT a.account_number, a.account_type, a.balance, a.status, a.created_at, "
        "c.customer_ID, c.name, c.email, c.phone, c.address, c.created_at AS joined "
        "FROM accounts a JOIN customers c ON a.customer_ID = c.customer_ID "
        "WHERE a.account_number = %s", (acct,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return None

    lines = []
    lines.append("  ===== CUSTOMER =====")
    lines.append("  Customer ID : " + row["customer_ID"])
    lines.append("  Name        : " + row["name"])
    lines.append("  Email       : " + (row["email"] or "-"))
    lines.append("  Phone       : " + (row["phone"] or "-"))
    lines.append("  Address     : " + (row["address"] or "-"))
    lines.append("  Joined      : " + str(row["joined"]))

    lines.append("  ===== ACCOUNT =====")
    lines.append("  Account No  : " + row["account_number"])
    lines.append("  Type        : " + row["account_type"])
    lines.append("  Balance     : " + str(round(float(row["balance"]), 2)))
    lines.append("  Status      : " + row["status"])
    lines.append("  Opened      : " + str(row["created_at"]))

    cursor.execute(
        "SELECT account_number, account_type, balance, status FROM accounts "
        "WHERE customer_ID = %s AND account_number <> %s",
        (row["customer_ID"], acct))
    others = cursor.fetchall()
    if others:
        lines.append("  ===== OTHER ACCOUNTS =====")
        for o in others:
            lines.append("    " + o["account_number"] + "  " + o["account_type"] +
                         "  bal " + str(round(float(o["balance"]), 2)) + "  " + o["status"])

    lines.append("  ===== RECENT TRANSACTIONS =====")
    cursor.execute(
        "SELECT type, amount, balance_after, timestamp FROM transactions "
        "WHERE account_ID = %s ORDER BY timestamp DESC LIMIT 5", (acct,))
    txns = cursor.fetchall()
    if not txns:
        lines.append("    (none)")
    else:
        for t in txns:
            lines.append("    " + str(t["timestamp"]) + "  " + t["type"] + "  " +
                         str(round(float(t["amount"]), 2)) + "  bal " +
                         str(round(float(t["balance_after"]), 2)))

    lines.append("  ===== LOANS =====")
    cursor.execute(
        "SELECT loan_ID, loan_type, purpose, amount, interest_rate, tenure_months, "
        "emi, penalty, amount_paid, remaining, status, applied_at, "
        "last_payment_date, next_due_date FROM loans "
        "WHERE customer_ID = %s ORDER BY applied_at DESC", (row["customer_ID"],))
    loans = cursor.fetchall()
    if not loans:
        lines.append("    (none)")
    else:
        for ln in loans:
            lines.append("    " + ln["loan_ID"] + "  (" + ln["loan_type"] + ")  " + ln["status"])
            lines.append("      Purpose   : " + (ln["purpose"] or "-"))
            lines.append("      Amount    : " + str(round(float(ln["amount"]), 2)) +
                         " @ " + str(ln["interest_rate"]) + "% for " +
                         str(ln["tenure_months"]) + " months")
            lines.append("      EMI       : " + str(round(float(ln["emi"]), 2)))
            lines.append("      Paid      : " + str(round(float(ln["amount_paid"]), 2)) +
                         "   Penalty: " + str(round(float(ln["penalty"]), 2)))
            lines.append("      Remaining : " + str(round(float(ln["remaining"]), 2)))
            lines.append("      Applied   : " + str(ln["applied_at"]))
            lines.append("      Last paid : " + str(ln["last_payment_date"] or "never") +
                         "   Next due: " + str(ln["next_due_date"] or "-"))
    cursor.close()
    return lines

def _save_report(acct, lines):
    filename = acct + "_details.txt"
    with open(filename, "w") as f:
        f.write("Customer Details Report\n")
        f.write("Account  : " + acct + "\n")
        f.write("Generated: " + str(date.today()) + "\n")
        f.write("=" * 44 + "\n")
        for ln in lines:
            f.write(ln + "\n")
    return filename

def find_customer():
    print("\n" + center("--- Find Customer by Account ---"))
    acct = get_text("Account number: ")
    lines = _customer_report(acct)
    if lines is None:
        say("No account found with number " + acct + ".")
        return
    say_block(lines)
    say("Saved to " + _save_report(acct, lines))

def transaction():
    print("\n" + center("--- New Transaction ---"))
    say("1) Deposit    2) Withdrawal    3) Transfer")
    choice = get_int("Choose (1-3): ")
    cursor = conn.cursor(dictionary=True)

    try:
        if choice == 3:
            src = get_text("Sender account number: ")
            src_info = _account_info(cursor, src)
            if not src_info:
                say("Sender account not found."); return
            if src_info["status"] != "ACTIVE":
                say("Sender account is not active."); return
            dst = get_text("Receiver account number: ")
            dst_info = _account_info(cursor, dst)
            if not dst_info:
                say("Receiver account not found."); return
            if src == dst:
                say("Cannot transfer to the same account."); return
            amount = get_amount("Amount to transfer: ")
            src_bal = float(src_info["balance"])
            if amount > src_bal:
                say("Insufficient balance."); return
            dst_bal = float(dst_info["balance"])

            _record(cursor, src, "TRANSFER_OUT", amount, round(src_bal - amount, 2),
                    sender_id=src, sender_name=src_info["name"],
                    receiver_id=dst, receiver_name=dst_info["name"])
            _record(cursor, dst, "TRANSFER_IN", amount, round(dst_bal + amount, 2),
                    sender_id=src, sender_name=src_info["name"],
                    receiver_id=dst, receiver_name=dst_info["name"])
            conn.commit()
            say("Transferred " + str(round(amount, 2)) + ": " + src + " -> " + dst)
            return

        if choice not in (1, 2):
            say("Invalid choice."); return

        acct = get_text("Account number: ")
        info = _account_info(cursor, acct)
        if not info:
            say("Account not found."); return
        if info["status"] != "ACTIVE":
            say("Account is not active."); return
        amount = get_amount("Amount: ")
        bal = float(info["balance"])
        if choice == 2 and amount > bal:
            say("Insufficient balance."); return

        tx_type = "DEPOSIT" if choice == 1 else "WITHDRAWAL"
        if choice == 1:
            new_balance = round(bal + amount, 2)
        else:
            new_balance = round(bal - amount, 2)
        _record(cursor, acct, tx_type, amount, new_balance)
        conn.commit()
        say(tx_type.title() + " of " + str(round(amount, 2)) +
            " OK. New balance: " + str(round(new_balance, 2)))

    except mysql.connector.Error as e:
        conn.rollback()
        say("Transaction failed: " + str(e))
    finally:
        cursor.close()

def loan():
    print("\n" + center("--- Apply for Loan ---"))
    cursor = conn.cursor(dictionary=True)
    cust = get_text("Customer ID: ")
    cursor.execute("SELECT name FROM customers WHERE customer_ID=%s", (cust,))
    row = cursor.fetchone()
    if not row:
        say("Customer not found."); cursor.close(); return
    say("Applicant: " + row["name"])
    say("Loan type:  1) PERSONAL   2) HOME   3) CAR   4) EDUCATION")
    ltype = {"1": "PERSONAL", "2": "HOME", "3": "CAR", "4": "EDUCATION"}.get(
        get_int("Choose (1-4): "), "PERSONAL")
    purpose = get_text("Purpose (optional): ", required=False)
    amount = get_amount("Principal amount: ")
    rate = get_float("Annual interest rate (%): ")
    tenure = get_int("Tenure (months): ")
    if tenure <= 0:
        say("Tenure must be positive."); cursor.close(); return

    emi = calc_emi(amount, rate, tenure)
    total = round(emi * tenure, 2)
    loan_id = next_id(cursor, "loans", "loan_ID", "LN")
    due = add_months(date.today(), 1)
    try:
        cursor.execute(
            "INSERT INTO loans "
            "(loan_ID, customer_ID, loan_type, purpose, amount, interest_rate, "
            "tenure_months, emi, remaining, status, next_due_date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING',%s)",
            (loan_id, cust, ltype, purpose, amount, rate, tenure, emi, total, due))
        conn.commit()
        say("Loan " + loan_id + " created (PENDING).")
        say("EMI = " + str(round(emi, 2)) + " x " + str(tenure) +
            " months | Total payable = " + str(round(total, 2)))
    except mysql.connector.Error as e:
        conn.rollback(); say("Could not create loan: " + str(e))
    finally:
        cursor.close()

def loan_payment():
    print("\n" + center("--- Pay Loan EMI ---"))
    cursor = conn.cursor(dictionary=True)
    loan_id = get_text("Loan ID: ")
    cursor.execute(
        "SELECT emi, tenure_months, penalty, amount_paid, remaining, "
        "status, next_due_date FROM loans WHERE loan_ID=%s", (loan_id,))
    ln = cursor.fetchone()
    if not ln:
        say("Loan not found."); cursor.close(); return
    if ln["status"] == "PAID":
        say("Loan already fully paid."); cursor.close(); return

    emi = float(ln["emi"])
    tenure = int(ln["tenure_months"])
    penalty = float(ln["penalty"])
    paid = float(ln["amount_paid"])
    remaining = float(ln["remaining"])
    due = ln["next_due_date"]

    say("Remaining before: " + str(round(remaining, 2)))
    amount = get_amount("Amount to pay: ")
    today = date.today()

    extra = 0.0
    if due and due < today:
        extra = 200.0
        say("Late payment (due " + str(due) + "). Penalty " + str(round(extra, 2)) + " applied.")

    new_paid = round(paid + amount, 2)
    new_penalty = round(penalty + extra, 2)
    total = round(emi * tenure + new_penalty, 2)
    new_remaining = round(total - new_paid, 2)
    if new_remaining <= 0:
        new_status = "PAID"
    elif ln["status"] == "PENDING":
        new_status = "APPROVED"
    else:
        new_status = ln["status"]
    if due:
        new_next = add_months(due, 1)
    else:
        new_next = add_months(today, 1)

    try:
        cursor.execute(
            "UPDATE loans SET amount_paid=%s, penalty=%s, remaining=%s, status=%s, "
            "last_payment_date=%s, next_due_date=%s WHERE loan_ID=%s",
            (new_paid, new_penalty, new_remaining, new_status, today, new_next, loan_id))
        conn.commit()
        say("Payment recorded. Remaining: " + str(round(new_remaining, 2)) +
            " | Status: " + new_status)
    except mysql.connector.Error as e:
        conn.rollback(); say("Payment failed: " + str(e))
    finally:
        cursor.close()

def view_account():
    print("\n" + center("--- Account Mini Statement ---"))
    acct = get_text("Account number: ")
    cursor = conn.cursor(dictionary=True)
    info = _account_info(cursor, acct)
    if not info:
        say("Account not found."); cursor.close(); return
    say_block([
        "  Holder : " + info["name"],
        "  Type   : " + info["account_type"] + "   Status: " + info["status"],
        "  Balance: " + str(round(float(info["balance"]), 2)),
    ])
    cursor.execute(
        "SELECT transaction_ID, type, amount, balance_after, timestamp "
        "FROM transactions WHERE account_ID=%s ORDER BY timestamp DESC LIMIT 10", (acct,))
    rows = cursor.fetchall()
    if not rows:
        say("No transactions yet.")
    else:
        say("Last transactions:")
        txns = []
        for r in rows:
            ts = str(r["timestamp"])
            txns.append("    " + ts + "  " + r["type"] + "  " +
                        str(round(float(r["amount"]), 2)) + "  bal " +
                        str(round(float(r["balance_after"]), 2)))
        say_block(txns)
    cursor.close()

def view_loan():
    print("\n" + center("--- Loan Status ---"))
    loan_id = get_text("Loan ID: ")
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT l.*, c.name FROM loans l "
        "JOIN customers c ON l.customer_ID = c.customer_ID WHERE l.loan_ID=%s", (loan_id,))
    r = cursor.fetchone()
    if not r:
        say("Loan not found."); cursor.close(); return
    say_block([
        "  Loan    : " + r["loan_ID"] + "   Applicant: " + r["name"],
        "  Type    : " + r["loan_type"] + "   Purpose: " + (r["purpose"] or "-"),
        "  Amount  : " + str(round(float(r["amount"]), 2)) + " @ " +
            str(r["interest_rate"]) + "% for " + str(r["tenure_months"]) + " months",
        "  EMI     : " + str(round(float(r["emi"]), 2)),
        "  Paid    : " + str(round(float(r["amount_paid"]), 2)) +
            "   Penalty: " + str(round(float(r["penalty"]), 2)),
        "  Remaining: " + str(round(float(r["remaining"]), 2)) +
            "   Status: " + r["status"],
        "  Last payment: " + str(r["last_payment_date"] or "never") +
            "   Next due: " + str(r["next_due_date"] or "-"),
    ])
    cursor.close()

def modify_customer():
    print("\n" + center("--- Modify Customer Details ---"))
    ref = get_text("Customer ID or Account number: ")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT customer_ID FROM customers WHERE customer_ID=%s", (ref,))
    found = cursor.fetchone()
    if found:
        cust = ref
    else:
        cursor.execute("SELECT customer_ID FROM accounts WHERE account_number=%s", (ref,))
        found = cursor.fetchone()
        cust = found["customer_ID"] if found else None
    if not cust:
        say("No customer or account found for '" + ref + "'.")
        cursor.close()
        return
    cursor.execute("SELECT name, email, phone, address FROM customers WHERE customer_ID=%s", (cust,))
    cur = cursor.fetchone()
    say("Current details for " + cust + ":")
    say("  Name    : " + cur["name"])
    say("  Email   : " + (cur["email"] or "-"))
    say("  Phone   : " + (cur["phone"] or "-"))
    say("  Address : " + (cur["address"] or "-"))
    say("(leave a field blank to keep its current value)")
    name = get_text("New name    [" + cur["name"] + "]: ", required=False)
    email = get_text("New email   [" + (cur["email"] or "") + "]: ", required=False)
    phone = get_text("New phone   [" + (cur["phone"] or "") + "]: ", required=False)
    address = get_text("New address [" + (cur["address"] or "") + "]: ", required=False)
    new_name = name if name else cur["name"]
    new_email = email if email else (cur["email"] or None)
    new_phone = phone if phone else (cur["phone"] or None)
    new_address = address if address else (cur["address"] or None)
    try:
        cursor.execute(
            "UPDATE customers SET name=%s, email=%s, phone=%s, address=%s "
            "WHERE customer_ID=%s",
            (new_name, new_email, new_phone, new_address, cust))
        conn.commit()
        say("Updated details for " + cust + ".")
    except mysql.connector.Error as e:
        conn.rollback()
        say("Update failed: " + str(e))
    finally:
        cursor.close()

def delete_customer():
    print("\n" + center("--- Delete Customer (Full) ---"))
    cust = get_text("Customer ID to delete: ")
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name FROM customers WHERE customer_ID=%s", (cust,))
    crow = cursor.fetchone()
    if not crow:
        say("No customer found with ID " + cust + ".")
        cursor.close()
        return
    cursor.execute(
        "SELECT loan_ID, status, remaining FROM loans "
        "WHERE customer_ID=%s AND status <> 'PAID'", (cust,))
    unpaid = cursor.fetchall()
    if unpaid:
        say("Cannot delete " + cust + " - it has unpaid loan(s):")
        for l in unpaid:
            say("  " + l["loan_ID"] + "   status " + l["status"] +
                "   remaining " + str(round(float(l["remaining"]), 2)))
        cursor.close()
        return
    cursor.execute(
        "SELECT account_number, balance FROM accounts WHERE customer_ID=%s", (cust,))
    accts = cursor.fetchall()
    say("Customer : " + cust + "  (" + crow["name"] + ")")
    if accts:
        for a in accts:
            say("  Account " + a["account_number"] +
                "   balance " + str(round(float(a["balance"]), 2)))
    else:
        say("  (no accounts)")
    confirm = get_text("Permanently delete " + cust + "? (Y/N): ", required=False)
    if not confirm or confirm.strip().upper() not in ("Y", "YES"):
        say("Deletion cancelled.")
        cursor.close()
        return
    try:
        for a in accts:
            cursor.execute("DELETE FROM transactions WHERE account_ID=%s",
                           (a["account_number"],))
        cursor.execute("DELETE FROM loans WHERE customer_ID=%s", (cust,))
        for a in accts:
            cursor.execute("DELETE FROM accounts WHERE account_number=%s",
                           (a["account_number"],))
        cursor.execute("DELETE FROM customers WHERE customer_ID=%s", (cust,))
        conn.commit()
        say("Deleted customer " + cust + " and all related data.")
    except mysql.connector.Error as e:
        conn.rollback()
        say("Delete failed: " + str(e))
    finally:
        cursor.close()
#endregion

#region Main Menu
def run_submenu(title, items):
    clear()
    header()
    while True:
        print("\n" + center("--- " + title + " ---"))
        for i in range(len(items)):
            print(center("  " + str(i + 1) + ") " + items[i][0]))
        print(center("  0) Back"))
        try:
            choice = get_int("Choose an option: ")
        except (KeyboardInterrupt, EOFError):
            return
        if choice == 0:
            return
        if 1 <= choice <= len(items):
            try:
                items[choice - 1][1]()
            except mysql.connector.Error as e:
                say("Database error: " + str(e))
            except (KeyboardInterrupt, EOFError):
                say("(cancelled)")
        else:
            say("Invalid choice.")

#endregion
