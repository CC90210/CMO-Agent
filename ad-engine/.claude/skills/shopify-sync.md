---
description: "Sync products from Shopify store. Use when products need updating, new products added, or images need refreshing."
---
# Shopify Product Sync

```bash
npm run shopify:sync
```

This fetches all products from the Shopify Storefront API (GraphQL) and saves:
- `public/products.json` — Product data (titles, prices, descriptions, variants)
- `public/products/<handle>/` — Product images (auto-downloaded)

Requires: `SHOPIFY_STORE_DOMAIN` and `SHOPIFY_STOREFRONT_ACCESS_TOKEN` in environment.

Run sync BEFORE rendering to ensure latest product data.