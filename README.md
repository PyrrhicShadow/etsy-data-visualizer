# Etsy Data Visualizer

Take manually sourced data and add it to Etsy's reports to create a single app to view and sort through Etsy sales trends over time (eventually). 

## Current features 

* Count orders by day of the week: finds which days are most busy for new orders
* Count orders by part of the month: shows whether buyers are more likely to buy at the beginning, middle, or end of any month
* SKU parser: turns order SKUs into a human-readable sentence
** Good for team members who help with shipping and packing 
* SKU cost lookup: breaks down materials costs of any order SKU 
* Unified SKU library for syncronized changes to sales offerings
* Existing Inventory and Recipe data for listings can be validated and automated 

## Current reports 

* Sales: breaks down each order by items purchased (by SKU), cost of materials, fees, earnings, and more! 
* Trends: aggrigates sales by date and shows buyer trends including hardware, flag or style, and more! 
** Can be automatically generated from a complete Sales file

## Future features 

* Sales file creator 
* Move towards one unified interactive CLI script leveraging other scripts instead of stand-alone-ish CLIs for every script
* GUI(?)