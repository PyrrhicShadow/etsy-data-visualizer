# Etsy Data Visualizer

Take manually sourced data and add it to Etsy's reports to create a single app to view and sort through Etsy sales trends over time (eventually). 

## Current features 

* Count orders by day of the week: finds which days are most busy for new orders
* Count orders by part of the month: shows whether buyers are more likely to buy at the beginning, middle, or end of any month
* SKU parser: turns order SKUs into a human-readable sentence
    * Good for team members who help with shipping and packaging 
* SKU cost lookup: breaks down materials costs of order SKU by charm, hardware, and packaging materials
* Unified SKU library for syncronized changes to sales offerings 
    * Flags when Recipe data or Trends are missing new SKU types
* Existing Inventory and Recipe data for listings can be validated and automated 
* Sales file creator/appender 
* Move towards one unified interactive CLI script leveraging other scripts instead of stand-alone-ish CLIs for every script

## Current reports 

* Sales: breaks down each order by items purchased (by SKU), cost of materials, fees, earnings, and more! 
    * Currently only accepts new sales. See future features for more info.
* Trends: aggrigates sales by date and shows buyer trends including hardware, flag or style, and more! 
    * Can be automatically generated from a complete Sales file.

## Future features 

* Sales file creator/appender 
    * Accept special rows such as refunds, cancelations, or insurance payouts
    * Import from Etsy financial reports, detect new sales, prompt user for SKU(s) of new sales
* Show most popular items over a specified time period 
    * ask for start/end dates
    * specify count of unique SKU, broad SKU (group together earrings, necklaces, bracelets of both types, phone charms), flags (Pride only), filter out Pride flags, etc
* Etsy Ads spending CSV import
* Implement bracelet & choker cost breakdown formula
* GUI(?)

## Etsy fees 

* listing fee: fixed $0.20 per sold listing 
    * example: if 3 items were sold in that order, 2 of 4B-LESBO5-LV and 1 of 4B-LESBO5-NK16, then I would be charged 3 listing fee instances ($0.60)
    * list $0.20 in the csv row so that final cost calculations column follows Excel rules of multiplying listing fee row amount by quantity of SKU purchased
* payment processing fee: 3% of payment amount + fixed $0.25
* transaction fee: 6.5% price of unique SKU sold (after discounts)
* shipping fee: 6.5% cost of shipping paid by customer
    * if the order has "free shipping", real shipping cost paid by me goes here
    * if the order has shipping paid by customer, shipping cost goes under "shipping price" and the 6.5% shipping fee goes here
    * specific historical orders have reshipment costs paid by me added here in addition to original shipping cost/fees
* Share & Save: 4% of order total refunded to me
    * Etsy seasonally changes exact percentage of Share & Save refunded as a promotion so this field should ask for an exact number, not an automatic calculation

## Sales CSV definitions

* Earnings: price after discount - (quantity * listing fee) - ( (sign of quantity) * payment fee) - ( (sign of quantity) * transaction fee) + Share & Save - ( (sign of quantity) * shipping fee) 
* Profit: earnings - (quantity * charm cost) - (quantity * finding cost) - (quantity * finding packaging cost) - envelope 
* Payment amount, shipping, and tax are only applied to the row of the first unique SKU of an order ID 
    * no defined sorting for unique SKUs with the same order ID, first inputted first listed 
