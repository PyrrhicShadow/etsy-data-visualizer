# Etsy Data Visualizer

Take manually sourced data and add it to Etsy's reports to create a single app to view and sort through Etsy sales trends over time (eventually). 

## Current features 

* Count orders by day of the week: finds which days are most busy for new orders
* Count orders by part of the month: shows whether buyers are more likely to buy at the beginning, middle, or end of any month
* SKU parser: turns order SKUs into a human-readable sentence
    * Good for team members who help with shipping and packaging 
* SKU cost lookup: breaks down materials costs of order SKU by charm, hardware, and packaging materials
* Unified SKU library for syncronized changes to sales offerings 
    * Shows when Recipe data or Trends are missing new SKU types
* Existing Inventory and Recipe data for listings can be validated and automated 
* Sales file creator/appender 
    * Add a fresh new sale by hand
    * bulk import missing orders from Etsy financial reports, detect new sales, prompt user for SKU(s) of new sales
    * appends to a temp file so you can double-check before adding to production data
* Show popular item trends over a specified time period 
    * Inclusive of start/end dates
    * Lists count of unique SKU, broad SKU (group together earrings, necklaces, bracelets of both types, phone charms), and shop categories (Pride flags, holidays, anime/video games, cottagecore, etc)
* Move towards one unified interactive CLI script leveraging other scripts instead of stand-alone-ish CLIs for every script 
    * new script still get a working stand-alone-ish CLI just for the purposes of testing before being added to the main CLI script

## Current reports 

* Sales: breaks down each order by items purchased (by SKU), cost of materials, fees, earnings, and more! 
    * Currently only accepts new sales. Refunds, cancels, and other miscellaneous rows still currently have to be manually entered. 
    * Now also imports / prefills new sales from downloaded Etsy sold order reports. 
* Trends: aggrigates sales by date and shows buyer trends including hardware, flag or style, and more! 
    * Can be automatically generated from a complete Sales file.
* Missing Recipes: Using all possible 4B Pride flag variations, looks for missing 4C, 6P, and 8R Pride recipes and creates their equivilents from the 4B recipes

## Future features 

* Sales file creator/appender 
    * Accept special rows such as refunds, cancelations, or insurance payouts
* Etsy Ads spending CSV import
* Implement bracelet & choker cost breakdown formula
* GUI(?)

----

## Etsy fees 

* `listing fee`: fixed $0.20 per sold listing 
    * example: if 3 items were sold in that order, 2 of 4B-LESBO5-LV and 1 of 4B-LESBO5-NK16, then I would be charged 3 listing fee instances ($0.60)
    * list $0.20 in the csv row so that final cost calculations column follows Excel rules of multiplying listing fee row amount by quantity of SKU purchased
* `payment processing fee`: 3% of payment amount + fixed $0.25
* `transaction fee`: 6.5% price of unique SKU sold (after discounts)
* `shipping fee`: 6.5% cost of shipping paid by customer
    * if the order has "free shipping", real shipping cost paid by me goes here
    * if the order has shipping paid by customer, shipping cost goes under "shipping price" and the 6.5% shipping fee goes here
    * specific historical orders have reshipment costs paid by me added here in addition to original shipping cost/fees
* `Share & Save`: 4% of order total refunded to me
    * Etsy seasonally changes exact percentage of Share & Save refunded as a promotion so this field should ask for an exact number, not an automatic calculation

## Sales CSV definitions

* `Earnings`: price after discount - (quantity * listing fee) - ( (sign of quantity) * payment fee) - ( (sign of quantity) * transaction fee) + Share & Save - ( (sign of quantity) * shipping fee) 
* `Profit`: earnings - (quantity * charm cost) - (quantity * finding cost) - (quantity * finding packaging cost) - envelope 
* Payment amount, shipping, and tax are only applied to the row of the first unique SKU of an order ID 
    * no defined sorting for unique SKUs with the same order ID, first inputted first listed 

## Etsy Sold Order Report definitions 

* order level CSV report is one line per **order**, not per unique SKU, unlike the sales CSV data 
* Etsy report `sales tax`: reports sales tax remitted by seller, which is usually $0, whereas `sales tax` in the sales CSV tracks sales tax paid by customer 
* Etsy report `shipping`: reports shipping costt added to order total to be paid by customer. 
    * `shipping ≥ 0`: free shipping - seller-paid shipping costs eat into profit 
    * `shipping > 0`: cusomer-paid shipping 