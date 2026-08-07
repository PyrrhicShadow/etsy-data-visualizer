# Define X.XX formatting for currency for amounts exported to CSV 
def currencyFormatCSV(num):
    return num

# Define $X.XX for positive values, $(X.XX) for negative values of currency for amounts displayed to UI
def currencyFormatUI(num): 
    return num

# Define {date.month}/{date.day}/{date.year} formatting for dates exported to CSV
def dateFormatCSV(date): 
    return date

# Define {day.strftime('%A, %B')} {day.day}, {day.year} formatting for dates displayed to UI
def dateFormatUI(date): 
    return date

# Define XXXX-XXX-XXX formatting for order numbers displayed to UI
def orderIDFormatUI(orderID):
    return orderID