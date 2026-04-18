/**
 * shopify_sync.js — Pull products from Shopify Storefront API → products.json
 *
 * Usage:
 *   SHOPIFY_STORE=mystore SHOPIFY_ACCESS_TOKEN=xxx node scripts/shopify_sync.js
 *   node scripts/shopify_sync.js --limit 10
 *
 * Output:
 *   products.json        — all products formatted as Remotion props
 *   public/products/     — first image for each product downloaded locally
 */

"use strict";

const fs = require("fs");
const path = require("path");
const https = require("https");

// Load .env from project root if present
try {
  require("dotenv").config({ path: path.join(__dirname, "..", ".env") });
} catch {
  // dotenv optional — env vars may already be set
}

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);
const limitFlag = args.indexOf("--limit");
const LIMIT = limitFlag !== -1 ? parseInt(args[limitFlag + 1], 10) : Infinity;

if (limitFlag !== -1 && isNaN(LIMIT)) {
  console.error("Error: --limit must be followed by a number.");
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const STORE = process.env.SHOPIFY_STORE;
const ACCESS_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

if (!STORE || !ACCESS_TOKEN) {
  console.error(
    "Error: SHOPIFY_STORE and SHOPIFY_ACCESS_TOKEN must be set.\n" +
      "  Set them as environment variables or add them to a .env file in the project root."
  );
  process.exit(1);
}

const GRAPHQL_ENDPOINT = `https://${STORE}.myshopify.com/api/2024-01/graphql.json`;
const PAGE_SIZE = 50; // Shopify max per page
const PRODUCTS_JSON = path.join(__dirname, "..", "products.json");
const IMAGES_DIR = path.join(__dirname, "..", "public", "products");

// ---------------------------------------------------------------------------
// GraphQL query — fetch one page of products
// ---------------------------------------------------------------------------

const PRODUCTS_QUERY = `
  query GetProducts($first: Int!, $after: String) {
    products(first: $first, after: $after) {
      pageInfo {
        hasNextPage
        endCursor
      }
      edges {
        node {
          id
          title
          description
          handle
          productType
          tags
          priceRange {
            minVariantPrice {
              amount
              currencyCode
            }
          }
          compareAtPriceRange {
            minVariantPrice {
              amount
              currencyCode
            }
          }
          images(first: 3) {
            edges {
              node {
                url
                altText
              }
            }
          }
          variants(first: 10) {
            edges {
              node {
                id
                title
                price {
                  amount
                  currencyCode
                }
                compareAtPrice {
                  amount
                  currencyCode
                }
                availableForSale
              }
            }
          }
        }
      }
    }
  }
`;

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

/**
 * POST a GraphQL query to the Shopify Storefront API.
 * Returns the parsed JSON response body.
 */
function graphqlRequest(query, variables) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ query, variables });

    const url = new URL(GRAPHQL_ENDPOINT);
    const options = {
      hostname: url.hostname,
      path: url.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
        "X-Shopify-Storefront-Access-Token": ACCESS_TOKEN,
        Accept: "application/json",
      },
    };

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        if (res.statusCode !== 200) {
          reject(
            new Error(
              `Shopify API returned HTTP ${res.statusCode}.\n` +
                `Response: ${data.slice(0, 500)}`
            )
          );
          return;
        }
        try {
          resolve(JSON.parse(data));
        } catch (err) {
          reject(new Error(`Failed to parse Shopify response: ${err.message}`));
        }
      });
    });

    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

/**
 * Download a file from a URL to a local path.
 * Skips download if the file already exists.
 */
function downloadFile(fileUrl, destPath) {
  return new Promise((resolve, reject) => {
    if (fs.existsSync(destPath)) {
      resolve(false); // already cached
      return;
    }

    const file = fs.createWriteStream(destPath);

    const request = (urlStr) => {
      const parsedUrl = new URL(urlStr);
      const mod = parsedUrl.protocol === "https:" ? https : require("http");

      mod
        .get(urlStr, (res) => {
          // Follow redirects (Shopify CDN sometimes redirects)
          if (
            res.statusCode >= 300 &&
            res.statusCode < 400 &&
            res.headers.location
          ) {
            request(res.headers.location);
            return;
          }

          if (res.statusCode !== 200) {
            file.close();
            fs.unlink(destPath, () => {});
            reject(new Error(`Image download failed: HTTP ${res.statusCode}`));
            return;
          }

          res.pipe(file);
          file.on("finish", () => {
            file.close();
            resolve(true);
          });
        })
        .on("error", (err) => {
          file.close();
          fs.unlink(destPath, () => {});
          reject(err);
        });
    };

    request(fileUrl);
  });
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

/**
 * Format a Shopify money amount + currencyCode into a display string.
 * e.g. { amount: "79.99", currencyCode: "USD" } → "$79.99"
 */
function formatPrice(moneyV2) {
  if (!moneyV2 || !moneyV2.amount) return null;

  const amount = parseFloat(moneyV2.amount);
  if (isNaN(amount) || amount === 0) return null;

  const symbols = {
    USD: "$",
    CAD: "CA$",
    EUR: "€",
    GBP: "£",
    AUD: "A$",
  };

  const symbol = symbols[moneyV2.currencyCode] ?? moneyV2.currencyCode + " ";
  return `${symbol}${amount.toFixed(2)}`;
}

/**
 * Calculate discount percentage between two Shopify MoneyV2 objects.
 * Returns a formatted string like "38% OFF" or null if no meaningful discount.
 */
function calculateDiscount(priceMoneyV2, compareAtMoneyV2) {
  if (!priceMoneyV2 || !compareAtMoneyV2) return null;

  const price = parseFloat(priceMoneyV2.amount);
  const compareAt = parseFloat(compareAtMoneyV2.amount);

  if (isNaN(price) || isNaN(compareAt) || compareAt <= 0 || price >= compareAt) {
    return null;
  }

  const pct = Math.round(((compareAt - price) / compareAt) * 100);
  return pct > 0 ? `${pct}% OFF` : null;
}

/**
 * Transform a raw Shopify product node into the shape expected by Remotion props.
 */
function transformProduct(node) {
  const price = node.priceRange?.minVariantPrice ?? null;
  const compareAt = node.compareAtPriceRange?.minVariantPrice ?? null;

  const images = (node.images?.edges ?? []).map((e) => e.node.url);

  const variants = (node.variants?.edges ?? []).map((e) => ({
    id: e.node.id,
    title: e.node.title,
    price: formatPrice(e.node.price),
    compareAtPrice: formatPrice(e.node.compareAtPrice),
    availableForSale: e.node.availableForSale,
  }));

  return {
    id: node.id,
    handle: node.handle,
    title: node.title,
    description: node.description || "",
    price: formatPrice(price),
    compareAtPrice: formatPrice(compareAt),
    discount: calculateDiscount(price, compareAt),
    images,
    productType: node.productType || "",
    tags: node.tags || [],
    variants,
  };
}

// ---------------------------------------------------------------------------
// Pagination — fetch all products
// ---------------------------------------------------------------------------

async function fetchAllProducts() {
  const products = [];
  let cursor = null;
  let hasNextPage = true;
  let page = 1;

  while (hasNextPage && products.length < LIMIT) {
    const pageSize = Math.min(PAGE_SIZE, LIMIT - products.length);

    process.stdout.write(`  Fetching page ${page}...`);

    const response = await graphqlRequest(PRODUCTS_QUERY, {
      first: pageSize,
      after: cursor,
    });

    if (response.errors?.length) {
      const messages = response.errors.map((e) => e.message).join(", ");
      throw new Error(`Shopify GraphQL errors: ${messages}`);
    }

    const pageData = response?.data?.products;
    if (!pageData) {
      throw new Error(
        "Unexpected Shopify response shape — no data.products field.\n" +
          "Check that your access token has the Storefront API scope."
      );
    }

    const nodes = pageData.edges.map((e) => transformProduct(e.node));
    products.push(...nodes);

    hasNextPage = pageData.pageInfo.hasNextPage;
    cursor = pageData.pageInfo.endCursor;
    page++;

    process.stdout.write(` ${nodes.length} products\n`);
  }

  return products;
}

// ---------------------------------------------------------------------------
// Image download — first image per product
// ---------------------------------------------------------------------------

async function downloadProductImages(products) {
  fs.mkdirSync(IMAGES_DIR, { recursive: true });

  let downloaded = 0;
  let skipped = 0;
  let failed = 0;

  for (const product of products) {
    const imageUrl = product.images[0];
    if (!imageUrl) continue;

    // Use the product handle as the filename, strip query params from extension
    const ext = imageUrl.split("?")[0].split(".").pop() || "jpg";
    const destPath = path.join(IMAGES_DIR, `${product.handle}.${ext}`);

    try {
      const wasDownloaded = await downloadFile(imageUrl, destPath);
      if (wasDownloaded) {
        downloaded++;
      } else {
        skipped++;
      }

      // Store the local path relative to Remotion's public/ dir so compositions
      // can reference it as a static asset via staticFile()
      product.localImage = `products/${product.handle}.${ext}`;
    } catch (err) {
      failed++;
      // Non-fatal — Remotion compositions can fall back to the remote URL
      process.stderr.write(
        `  Warning: Could not download image for "${product.title}": ${err.message}\n`
      );
    }
  }

  return { downloaded, skipped, failed };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log(`\nShopify Sync — ${STORE}.myshopify.com`);
  console.log("─".repeat(50));

  if (isFinite(LIMIT)) {
    console.log(`Mode: limited to first ${LIMIT} products\n`);
  } else {
    console.log("Mode: all products\n");
  }

  // 1. Fetch products
  let products;
  try {
    products = await fetchAllProducts();
  } catch (err) {
    console.error(`\nFetch failed: ${err.message}`);
    process.exit(1);
  }

  if (products.length === 0) {
    console.warn("\nNo products returned. Check that your store has published products.");
    process.exit(0);
  }

  console.log(`\nFetched ${products.length} products. Downloading images...\n`);

  // 2. Download first image for each product
  const imageStats = await downloadProductImages(products);

  // 3. Write products.json
  try {
    fs.writeFileSync(PRODUCTS_JSON, JSON.stringify(products, null, 2), "utf8");
  } catch (err) {
    console.error(`\nFailed to write products.json: ${err.message}`);
    process.exit(1);
  }

  // 4. Summary
  console.log("\n" + "─".repeat(50));
  console.log(`Synced ${products.length} products from ${STORE}`);
  console.log(
    `Images: ${imageStats.downloaded} downloaded, ${imageStats.skipped} cached, ${imageStats.failed} failed`
  );
  console.log(`Output: ${PRODUCTS_JSON}`);
  console.log(`Images: ${IMAGES_DIR}\n`);
}

main();
