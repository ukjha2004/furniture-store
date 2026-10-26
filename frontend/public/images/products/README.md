# Product photos

One photo per product, named by product id: `1.jpg`, `2.jpg`, ... `200.jpg`.

The full list (which id is which product, and what to search for) is in
`docs/product-photos.csv` at the root of the repo. Open it in Excel or Google Sheets.

- Free photos: https://unsplash.com or https://www.pexels.com
- Use the "Small" / ~640px download so each file stays under ~150 KB
- File names must be exactly `<id>.jpg`, lowercase `.jpg` (check for `1.jpg.jpg` on Windows!)

You don't have to add all 200 at once. Any product without its own photo
automatically shows its category photo (`../sofas.jpg` etc.), then a coloured tile.
